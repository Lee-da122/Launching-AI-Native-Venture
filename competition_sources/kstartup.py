import html
import json
import os
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .base import CompetitionRecord

SOURCE_NAME = "K-Startup"
KOREA_TZ = ZoneInfo("Asia/Seoul")
API_URL = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
USER_AGENT = "TeamMatch-Competition-Sync/1.0 (+https://teammatch-production.up.railway.app)"
DEFAULT_TIMEOUT = 15
MAX_RETRIES = 2
PAGE_SIZE = 100
MAX_PAGES = 5  # MVP safety limit: current/recent announcements only.

COMPETITION_KEYWORDS = (
    "공모전", "경진대회", "아이디어", "해커톤", "챌린지", "피칭", "데모데이", "경연", "대회"
)
STUDENT_RELEVANCE_KEYWORDS = (
    "대학생", "대학원생", "청년", "일반인", "제한 없음", "예비창업자", "예비 창업자"
)


def _clean_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_yyyymmdd(value: Any):
    raw = re.sub(r"\D", "", str(value or ""))
    if len(raw) != 8:
        return None
    try:
        return datetime.strptime(raw, "%Y%m%d").date()
    except ValueError:
        return None


def _participation_type(text: str):
    compact = text.replace(" ", "")
    has_team = "팀" in compact
    has_individual = "개인" in compact or "1인" in compact
    if has_team and has_individual:
        return "Individual or team"
    if has_team:
        return "Team"
    if has_individual:
        return "Individual"
    return None


def _category(row: dict[str, Any], title: str) -> str | None:
    combined = f"{title} {_clean_text(row.get('supt_biz_clsfc'))}".lower()
    mappings = [
        (("ai", "인공지능", "데이터"), "Data / AI"),
        (("디자인",), "Design"),
        (("마케팅", "광고"), "Marketing"),
        (("환경", "탄소", "지속가능", "esg"), "Sustainability"),
        (("공학", "로봇", "모빌리티", "기술"), "Engineering"),
        (("창업", "스타트업", "피칭", "데모데이", "사업화"), "Startup / Business"),
        (("아이디어", "기획"), "Idea / Planning"),
    ]
    for words, label in mappings:
        if any(word in combined for word in words):
            return label
    return _clean_text(row.get("supt_biz_clsfc")) or None


def is_relevant(row: dict[str, Any]) -> bool:
    title = _clean_text(row.get("biz_pbanc_nm"))
    content = " ".join(
        _clean_text(row.get(k))
        for k in ("pbanc_ctnt", "aply_trgt", "aply_trgt_ctnt", "intg_pbanc_biz_nm")
    )
    if not any(k.lower() in title.lower() or k.lower() in content.lower() for k in COMPETITION_KEYWORDS):
        return False
    audience = f"{_clean_text(row.get('aply_trgt'))} {_clean_text(row.get('aply_trgt_ctnt'))} {title}"
    return any(k.lower() in audience.lower() for k in STUDENT_RELEVANCE_KEYWORDS)


def normalize_record(row: dict[str, Any], fetched_at: datetime | None = None) -> CompetitionRecord:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    title = _clean_text(row.get("biz_pbanc_nm"))
    external_id = _clean_text(row.get("pbanc_sn"))
    if not title or not external_id:
        raise ValueError("K-Startup record is missing title or stable announcement id")

    start_date = _parse_yyyymmdd(row.get("pbanc_rcpt_bgng_dt"))
    end_date = _parse_yyyymmdd(row.get("pbanc_rcpt_end_dt"))
    raw_end = _clean_text(row.get("pbanc_rcpt_end_dt")) or None
    open_flag = _clean_text(row.get("rcrt_prgs_yn")).upper()
    active = open_flag != "N" and (end_date is None or end_date >= datetime.now(KOREA_TZ).date())

    eligibility_parts = [
        _clean_text(row.get("aply_trgt")),
        _clean_text(row.get("aply_trgt_ctnt")),
    ]
    eligibility = " · ".join(p for p in eligibility_parts if p) or None
    description = _clean_text(row.get("pbanc_ctnt"))
    if not description:
        description = "See original competition page for details."
    elif len(description) > 420:
        description = description[:417].rstrip() + "..."

    source_url = _clean_text(row.get("detl_pg_url")) or _clean_text(row.get("biz_gdnc_url"))
    if source_url and not source_url.startswith(("http://", "https://")):
        source_url = "https://" + source_url.lstrip("/")
    if not source_url:
        source_url = "https://www.k-startup.go.kr/"

    organizer = _clean_text(row.get("pbanc_ntrp_nm")) or _clean_text(row.get("sprv_inst")) or None
    participation_text = f"{eligibility or ''} {description}"

    return CompetitionRecord(
        name=title,
        organizer=organizer,
        deadline=end_date.isoformat() if end_date else None,
        deadline_date=end_date,
        description=description,
        category=_category(row, title),
        eligibility=eligibility,
        participation_type=_participation_type(participation_text),
        source_name=SOURCE_NAME,
        source_url=source_url,
        external_id=external_id,
        fetched_at=fetched_at,
        application_start_date=start_date,
        original_deadline_text=raw_end,
        is_active=active,
    )


def _extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("data", "items", "item"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            nested = value.get("item")
            if isinstance(nested, list):
                return [x for x in nested if isinstance(x, dict)]
    response = payload.get("response")
    if isinstance(response, dict):
        body = response.get("body", {})
        items = body.get("items", {}) if isinstance(body, dict) else {}
        if isinstance(items, dict):
            item = items.get("item", [])
            if isinstance(item, dict):
                return [item]
            if isinstance(item, list):
                return [x for x in item if isinstance(x, dict)]
    return []


def fetch_page(service_key: str, page: int, per_page: int = PAGE_SIZE) -> dict[str, Any]:
    params = {
        "serviceKey": service_key,
        "page": page,
        "perPage": per_page,
        "returnType": "json",
        "cond[rcrt_prgs_yn::EQ]": "Y",
    }
    url = API_URL + "?" + urlencode(params)
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
                raw = response.read().decode("utf-8")
            return json.loads(raw)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt >= MAX_RETRIES:
                break
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"K-Startup API request failed after retries: {last_error}")


def fetch_competitions(service_key: str | None = None) -> tuple[list[CompetitionRecord], dict[str, int]]:
    key = (service_key or os.getenv("K_STARTUP_SERVICE_KEY", "")).strip()
    if not key:
        raise RuntimeError("K_STARTUP_SERVICE_KEY is required for live K-Startup synchronization.")

    records: list[CompetitionRecord] = []
    fetched = 0
    parsed = 0
    skipped = 0
    errors = 0
    fetched_at = datetime.now(timezone.utc)

    for page in range(1, MAX_PAGES + 1):
        payload = fetch_page(key, page, PAGE_SIZE)
        rows = _extract_rows(payload)
        if not rows:
            break
        fetched += len(rows)
        for row in rows:
            try:
                if not is_relevant(row):
                    skipped += 1
                    continue
                records.append(normalize_record(row, fetched_at=fetched_at))
                parsed += 1
            except Exception:
                errors += 1
        if len(rows) < PAGE_SIZE:
            break
        time.sleep(0.5)

    return records, {"fetched": fetched, "parsed": parsed, "skipped": skipped, "errors": errors}
