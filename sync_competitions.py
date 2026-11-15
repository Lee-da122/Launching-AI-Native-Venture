import re
import unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from competition_sources.kstartup import SOURCE_NAME as KSTARTUP_SOURCE, fetch_competitions as fetch_kstartup
from competition_sources.wevity import SOURCE_NAME as WEVITY_SOURCE, fetch_competitions as fetch_wevity
from db import get_db, init_db

KOREA_TZ = ZoneInfo("Asia/Seoul")
KNOWN_LIVE_SOURCES = (KSTARTUP_SOURCE, WEVITY_SOURCE)
SOURCE_PRIORITY = {KSTARTUP_SOURCE: 2, WEVITY_SOURCE: 1}


def _norm_identity(value):
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"[^0-9a-z가-힣]+", "", text)
    return text


def _find_cross_source_duplicate(conn, record):
    """Conservative exact-ish fingerprint: normalized title + organizer + deadline."""
    if not record.deadline_date:
        return None
    rows = conn.execute(
        """SELECT id, name, organizer, deadline_date, source_name, external_id
           FROM competitions WHERE deadline_date = :deadline_date""",
        {"deadline_date": record.deadline_date},
    ).fetchall()
    name_key = _norm_identity(record.name)
    org_key = _norm_identity(record.organizer)
    for row in rows:
        if _norm_identity(row["name"]) != name_key:
            continue
        existing_org = _norm_identity(row.get("organizer"))
        if org_key and existing_org and existing_org != org_key:
            continue
        return row
    return None


def upsert_records(records):
    conn = get_db()
    new_count = 0
    updated_count = 0
    merged_count = 0
    errored = 0
    try:
        for record in records:
            try:
                existing = conn.execute(
                    """SELECT id, source_name, external_id FROM competitions
                       WHERE source_name = :source_name AND external_id = :external_id""",
                    {"source_name": record.source_name, "external_id": record.external_id},
                ).fetchone()
                cross_source = False
                if not existing:
                    existing = _find_cross_source_duplicate(conn, record)
                    cross_source = existing is not None

                params = {
                    "name": record.name,
                    "organizer": record.organizer,
                    "deadline": record.deadline,
                    "deadline_date": record.deadline_date,
                    "description": record.description,
                    "category": record.category,
                    "eligibility": record.eligibility,
                    "participation_type": record.participation_type,
                    "source_name": record.source_name,
                    "source_url": record.source_url,
                    "external_id": record.external_id,
                    "fetched_at": record.fetched_at,
                    "updated_at": datetime.now(timezone.utc),
                    "is_active": record.is_active,
                    "application_start_date": record.application_start_date,
                    "original_deadline_text": record.original_deadline_text,
                }
                if existing:
                    params["id"] = existing["id"]
                    # If a duplicate exists across sources, keep provenance from the higher-priority
                    # official source. The TeamMatch row id never changes.
                    existing_source = existing.get("source_name")
                    incoming_priority = SOURCE_PRIORITY.get(record.source_name, 0)
                    existing_priority = SOURCE_PRIORITY.get(existing_source, 0)
                    preserve_existing_provenance = cross_source and existing_priority > incoming_priority
                    if preserve_existing_provenance:
                        conn.execute(
                            """UPDATE competitions SET
                               name=:name, organizer=:organizer, deadline=:deadline,
                               deadline_date=:deadline_date,
                               category=COALESCE(:category, category),
                               eligibility=COALESCE(:eligibility, eligibility),
                               participation_type=COALESCE(:participation_type, participation_type),
                               fetched_at=:fetched_at, updated_at=:updated_at,
                               is_active=:is_active,
                               application_start_date=COALESCE(:application_start_date, application_start_date),
                               original_deadline_text=COALESCE(:original_deadline_text, original_deadline_text)
                               WHERE id=:id""",
                            params,
                        )
                    else:
                        conn.execute(
                            """UPDATE competitions SET
                               name=:name, organizer=:organizer, deadline=:deadline,
                               deadline_date=:deadline_date, description=:description,
                               category=:category, eligibility=:eligibility,
                               participation_type=:participation_type, source_name=:source_name,
                               source_url=:source_url, external_id=:external_id,
                               fetched_at=:fetched_at, updated_at=:updated_at,
                               is_active=:is_active, application_start_date=:application_start_date,
                               original_deadline_text=:original_deadline_text
                               WHERE id=:id""",
                            params,
                        )
                    updated_count += 1
                    if cross_source:
                        merged_count += 1
                else:
                    conn.execute(
                        """INSERT INTO competitions(
                           name, organizer, deadline, deadline_date, description, category,
                           eligibility, participation_type, source_name, source_url, external_id,
                           fetched_at, updated_at, is_active, application_start_date,
                           original_deadline_text)
                           VALUES (:name, :organizer, :deadline, :deadline_date, :description, :category,
                           :eligibility, :participation_type, :source_name, :source_url, :external_id,
                           :fetched_at, :updated_at, :is_active, :application_start_date,
                           :original_deadline_text)""",
                        params,
                    )
                    new_count += 1
            except Exception:
                errored += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"new": new_count, "updated": updated_count, "merged": merged_count, "db_errors": errored}


def mark_expired_records():
    conn = get_db()
    today = datetime.now(KOREA_TZ).date()
    total = 0
    for source_name in KNOWN_LIVE_SOURCES:
        result = conn.execute(
            """UPDATE competitions
               SET is_active = :inactive, updated_at = :updated_at
               WHERE source_name = :source_name
                 AND deadline_date IS NOT NULL
                 AND deadline_date < :today
                 AND is_active = :active""",
            {
                "inactive": False,
                "active": True,
                "source_name": source_name,
                "today": today,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        if result.rowcount and result.rowcount > 0:
            total += result.rowcount
    conn.commit()
    conn.close()
    return total


def run_sync(fetchers=None):
    init_db()
    fetchers = fetchers or [
        (KSTARTUP_SOURCE, fetch_kstartup),
        (WEVITY_SOURCE, fetch_wevity),
    ]
    start = datetime.now(timezone.utc)
    print(f"Competition sync started: {start.isoformat()} sources={','.join(name for name, _ in fetchers)}")

    totals = {"fetched": 0, "parsed": 0, "skipped": 0, "errors": 0, "source_failures": 0}
    source_results = {}
    any_source_succeeded = False
    all_records = []

    for source_name, fetcher in fetchers:
        try:
            records, stats = fetcher()
            any_source_succeeded = True
            all_records.extend(records)
            source_results[source_name] = {"status": "ok", **stats}
            for key in ("fetched", "parsed", "skipped", "errors"):
                totals[key] += int(stats.get(key, 0))
            print(
                f"Source complete: {source_name} "
                f"Fetched={stats.get('fetched', 0)} Parsed={stats.get('parsed', 0)} "
                f"Skipped={stats.get('skipped', 0)} Errors={stats.get('errors', 0)}"
            )
        except Exception as exc:
            totals["source_failures"] += 1
            source_results[source_name] = {"status": "failed", "error": str(exc)}
            print(f"Source failed safely: {source_name}: {exc}")

    if not any_source_succeeded:
        print("Competition sync failed safely: all sources unavailable.")
        print("Existing competition data was preserved.")
        return 1, {**totals, "source_failure": True, "sources": source_results}

    db_stats = upsert_records(all_records)
    expired = mark_expired_records()
    summary = {**totals, **db_stats, "expired_marked": expired, "sources": source_results}
    print(
        "Competition sync complete: "
        f"Fetched={summary['fetched']} Parsed={summary['parsed']} "
        f"New={summary['new']} Updated={summary['updated']} Merged={summary['merged']} "
        f"Skipped={summary['skipped']} "
        f"Errors={summary['errors'] + summary['db_errors']} "
        f"SourceFailures={summary['source_failures']} ExpiredMarked={expired}"
    )
    return 0, summary


if __name__ == "__main__":
    code, _ = run_sync()
    raise SystemExit(code)
