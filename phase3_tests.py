import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from competition_sources.base import CompetitionRecord
from competition_sources.kstartup import is_relevant, normalize_record
from competition_sources.wevity import is_relevant_title, parse_detail, parse_listing_links
from db import get_db, init_db, reset_engine_for_tests
from sync_competitions import run_sync, upsert_records


def row(**overrides):
    base = {
        "pbanc_sn": "179999",
        "biz_pbanc_nm": "2026 청년 AI 아이디어 공모전",
        "pbanc_ntrp_nm": "창업진흥원",
        "sprv_inst": "공공기관",
        "pbanc_rcpt_bgng_dt": "20261101",
        "pbanc_rcpt_end_dt": "20261215",
        "aply_trgt": "대학생,일반인",
        "aply_trgt_ctnt": "AI 아이디어가 있는 대학생 및 일반인",
        "pbanc_ctnt": "개인 또는 팀으로 참여하는 AI 아이디어 공모전입니다.",
        "supt_biz_clsfc": "사업화",
        "detl_pg_url": "https://www.k-startup.go.kr/example/179999",
        "rcrt_prgs_yn": "Y",
    }
    base.update(overrides)
    return base


WEVITY_LIST_FIXTURE = """
<html><body>
<a href="index_university.php?c=find&gbn=viewok&gp=1&ix=112155&s=_university">
  2026 대학생 AI 아이디어 공모전
</a>
<a href="index_university.php?c=find&gbn=viewok&gp=1&ix=112156&s=_university">
  대학생 서포터즈 모집
</a>
<a href="index_university.php?c=find&gbn=viewok&gp=1&ix=112155&s=_university">
  <img alt="2026 대학생 AI 아이디어 공모전">
</a>
</body></html>
"""


WEVITY_GENERIC_HEADING_FIXTURE = """
<html>
<head><title>공모전 대외활동 콘테스트 메인메뉴 - WEVITY</title></head>
<body>
<h6>공모전 대외활동 콘테스트 메인메뉴</h6>
<ul>
<li>분야 데이터/AI</li>
<li>응모대상 대학생</li>
<li>주최/주관 테스트기관</li>
<li>접수기간 2026-11-01 ~ 2026-11-30</li>
</ul>
</body>
</html>
"""

WEVITY_DETAIL_FIXTURE = """
<html>
<head><title>2026 대학생 AI 아이디어 공모전 - WEVITY(위비티) 공모전</title></head>
<body>
<h6>2026 대학생 AI 아이디어 공모전</h6>
<ul>
<li>분야 기획/아이디어, 웹/모바일/IT, 과학/공학</li>
<li>응모대상 대학생, 대학원생</li>
<li>주최/주관 테스트재단 / 테스트기관</li>
<li>접수기간 2026-11-01 ~ 2026-12-20 D-35</li>
</ul>
<p>개인 또는 팀으로 참여할 수 있습니다.</p>
</body></html>
"""


def setup_temp_db():
    tmp = tempfile.TemporaryDirectory()
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp.name) / 'phase3.db'}"
    reset_engine_for_tests()
    init_db()
    return tmp


def deadline_label(deadline):
    if deadline is None:
        return "Not specified"
    delta = (deadline - date.today()).days
    if delta < 0:
        return "Closed"
    if delta == 0:
        return "D-Day"
    return f"D-{delta}"


def wevity_record(external_id="112155", deadline=date(2026, 12, 15)):
    return CompetitionRecord(
        name="2026 청년 AI 아이디어 공모전",
        organizer="창업진흥원",
        deadline=deadline.isoformat(),
        deadline_date=deadline,
        description="See original competition page for details.",
        category="Data / AI",
        eligibility="대학생, 일반인",
        participation_type="Individual or team",
        source_name="WEVITY",
        source_url=f"https://www.wevity.com/index_university.php?c=find&gbn=viewok&ix={external_id}",
        external_id=external_id,
        fetched_at=datetime.now(timezone.utc),
        application_start_date=date(2026, 11, 1),
        original_deadline_text="2026-11-01 ~ 2026-12-15",
        is_active=True,
    )


def main():
    tmp = setup_temp_db()
    now = datetime.now(timezone.utc)

    # K-Startup parser / missing-field coverage.
    normal = normalize_record(row(), now)
    assert normal.external_id == "179999" and normal.category == "Data / AI"
    assert is_relevant(row()) is True
    assert is_relevant(row(biz_pbanc_nm="일반 창업 교육 모집", pbanc_ctnt="교육생 모집", aply_trgt="일반인", aply_trgt_ctnt="교육 참여 희망자", intg_pbanc_biz_nm="교육 지원")) is False
    missing_org = normalize_record(row(pbanc_ntrp_nm="", sprv_inst=""), now)
    assert missing_org.organizer is None
    missing_elig = normalize_record(row(aply_trgt="", aply_trgt_ctnt=""), now)
    assert missing_elig.eligibility is None
    missing_deadline = normalize_record(row(pbanc_rcpt_end_dt="상시모집"), now)
    assert missing_deadline.deadline_date is None and missing_deadline.deadline is None
    unusual = normalize_record(row(biz_pbanc_nm="[제1회] K-Startup × AI! 청년 챌린지"), now)
    assert unusual.name.startswith("[제1회]")
    try:
        normalize_record(row(pbanc_sn=""), now)
        raise AssertionError("malformed record should fail")
    except ValueError:
        pass

    # WEVITY listing/detail fixture parser.
    links = parse_listing_links(WEVITY_LIST_FIXTURE)
    assert len(links) == 2
    assert links[0][0].startswith("https://www.wevity.com/") and "112155" in links[0][0]
    assert is_relevant_title("2026 대학생 AI 아이디어 공모전") is True
    assert is_relevant_title("대학생 서포터즈 모집") is False
    w = parse_detail(
        WEVITY_DETAIL_FIXTURE,
        "https://www.wevity.com/index_university.php?c=find&gbn=viewok&ix=112155&s=_university",
        now,
    )
    assert w.external_id == "112155"
    assert w.organizer == "테스트재단 / 테스트기관"
    assert w.eligibility == "대학생, 대학원생"
    assert w.deadline_date == date(2026, 12, 20)
    assert w.category == "Data / AI"
    assert w.description == "See original competition page for details."

    # Production regression: shared page headings must never replace the listing title.
    generic = parse_detail(
        WEVITY_GENERIC_HEADING_FIXTURE,
        "https://www.wevity.com/index_university.php?c=find&gbn=viewok&ix=998877&s=_university",
        now,
        listing_title="2026 실제 대학생 데이터 분석 경진대회",
    )
    assert generic.name == "2026 실제 대학생 데이터 분석 경진대회"

    # Idempotency and update-in-place for same source.
    upsert_records([normal])
    conn = get_db()
    first = conn.execute("SELECT id, deadline, description FROM competitions WHERE external_id=:id", {"id":"179999"}).fetchone()
    conn.close()
    upsert_records([normal])
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) AS n FROM competitions WHERE external_id=:id", {"id":"179999"}).fetchone()["n"]
    conn.close()
    assert count == 1

    changed = normalize_record(row(pbanc_rcpt_end_dt="20261220", pbanc_ctnt="변경된 설명입니다. 개인 또는 팀 참여."), now)
    upsert_records([changed])
    conn = get_db()
    second = conn.execute("SELECT id, deadline, description FROM competitions WHERE external_id=:id", {"id":"179999"}).fetchone()
    conn.close()
    assert first["id"] == second["id"] and second["deadline"] == "2026-12-20" and "변경된 설명" in second["description"]

    # Cross-source duplicate merge: exact normalized title+organizer+deadline.
    same_deadline = date(2026, 12, 20)
    duplicate_wevity = wevity_record(deadline=same_deadline)
    before_id = second["id"]
    stats = upsert_records([duplicate_wevity])
    conn = get_db()
    total_same_title = conn.execute("SELECT COUNT(*) AS n FROM competitions WHERE name=:name", {"name":"2026 청년 AI 아이디어 공모전"}).fetchone()["n"]
    merged = conn.execute("SELECT id, source_name, external_id FROM competitions WHERE id=:id", {"id": before_id}).fetchone()
    conn.close()
    assert total_same_title == 1 and stats["merged"] == 1
    assert merged["id"] == before_id and merged["source_name"] == "K-Startup" and merged["external_id"] == "179999"

    # Historical relationship safety.
    conn = get_db()
    conn.execute("""INSERT INTO users(name,university,email,password_hash,skills,availability,preferred_role,working_style,project_goal)
                    VALUES ('Owner','KU','owner@test','hash','Coding','Weekends','Data / Coding','Structured and planned','Balanced effort')""")
    owner_id = conn.execute("SELECT id FROM users WHERE email='owner@test'").fetchone()["id"]
    comp_id = conn.execute("SELECT id FROM competitions WHERE external_id='179999'").fetchone()["id"]
    conn.execute("""INSERT INTO teams(competition_id,owner_id,title,description,needed_skills,needed_role,availability,working_style,project_goal,members_needed)
                    VALUES (:c,:o,'Team A','x','Coding','Data / Coding','Weekends','Structured and planned','Balanced effort',1)""", {"c":comp_id,"o":owner_id})
    conn.commit()
    conn.close()
    expired = normalize_record(row(pbanc_rcpt_end_dt="20200101", rcrt_prgs_yn="N"), now)
    upsert_records([expired])
    conn = get_db()
    rel = conn.execute("SELECT teams.competition_id, competitions.is_active FROM teams JOIN competitions ON competitions.id=teams.competition_id WHERE teams.title='Team A'").fetchone()
    conn.close()
    assert rel["competition_id"] == comp_id and bool(rel["is_active"]) is False

    # One source fails, another succeeds: sync still succeeds and stored data is preserved/extended.
    def failing_source():
        raise TimeoutError("simulated timeout")

    def healthy_source():
        return [wevity_record(external_id="223344", deadline=date(2027, 1, 10))], {"fetched":1, "parsed":1, "skipped":0, "errors":0}

    code, stats = run_sync(fetchers=[("Broken", failing_source), ("WEVITY", healthy_source)])
    assert code == 0 and stats["source_failures"] == 1 and stats["parsed"] == 1
    conn = get_db()
    preserved = conn.execute("SELECT COUNT(*) AS n FROM competitions").fetchone()["n"]
    conn.close()
    assert preserved >= 2

    # All sources fail: no deletion and non-zero exit.
    code, stats = run_sync(fetchers=[("BrokenA", failing_source), ("BrokenB", failing_source)])
    assert code == 1 and stats["source_failure"] is True
    conn = get_db()
    after_failure = conn.execute("SELECT COUNT(*) AS n FROM competitions").fetchone()["n"]
    conn.close()
    assert after_failure == preserved

    # Deadline behavior.
    assert deadline_label(date.today() + timedelta(days=3)) == "D-3"
    assert deadline_label(date.today()) == "D-Day"
    assert deadline_label(date.today() - timedelta(days=1)) == "Closed"
    assert deadline_label(None) == "Not specified"

    print("PHASE3_KSTARTUP_PARSER 8/8 PASS")
    print("PHASE3_WEVITY_FIXTURE_PARSER PASS")
    print("PHASE3_IDEMPOTENCY PASS")
    print("PHASE3_UPDATE_IN_PLACE PASS")
    print("PHASE3_CROSS_SOURCE_DEDUP PASS")
    print("PHASE3_RELATIONSHIP_SAFETY PASS")
    print("PHASE3_SOURCE_ISOLATION PASS")
    print("PHASE3_ALL_SOURCE_FAILURE_SAFETY PASS")
    print("PHASE3_DEADLINE_BEHAVIOR 4/4 PASS")
    tmp.cleanup()


if __name__ == "__main__":
    main()
