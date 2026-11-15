import html
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .base import CompetitionRecord

SOURCE_NAME = "WEVITY"
KOREA_TZ = ZoneInfo("Asia/Seoul")
BASE_URL = "https://www.wevity.com/"
LIST_URL = "https://www.wevity.com/index_university.php?c=find&gbn=list&mode=ing&s=_university&gp={page}"
USER_AGENT = "TeamMatch-Competition-Sync/1.0 (+https://teammatch-production.up.railway.app)"
DEFAULT_TIMEOUT = 15
MAX_RETRIES = 1
MAX_PAGES = 2
MAX_DETAIL_REQUESTS = 40
REQUEST_DELAY_SECONDS = 0.7

COMPETITION_WORDS = (
    "공모전", "경진대회", "대회", "콘테스트", "챌린지", "해커톤", "아이디어", "논문", "경연대회"
)
EXCLUDE_ONLY_WORDS = (
    "서포터즈 모집", "기자단 모집", "봉사단 모집", "멘토링", "아카데미", "교육생 모집",
    "홍보대사 모집", "체험단 모집", "인턴 모집", "채용", "이벤트"
)


def _clean(value):
    value = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def _request_text(url: str) -> str:
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
            with urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
            try:
                return raw.decode(charset, errors="replace")
            except LookupError:
                return raw.decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt >= MAX_RETRIES:
                break
            time.sleep(1.0)
    raise RuntimeError(f"WEVITY request failed after retries: {last_error}")


def parse_listing_links(page_html: str) -> list[tuple[str, str]]:
    """Return (detail_url, title) from the public university contest listing."""
    soup = BeautifulSoup(page_html, "html.parser")
    results = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if "ix=" not in href or "gbn=view" not in href:
            continue
        title = _clean(anchor.get_text(" ", strip=True))
        if not title:
            img = anchor.find("img")
            title = _clean(img.get("alt")) if img else ""
        if not title:
            continue
        url = urljoin(BASE_URL, href)
        query = parse_qs(urlparse(url).query)
        external_id = (query.get("ix") or [""])[0]
        if not external_id or external_id in seen:
            continue
        seen.add(external_id)
        results.append((url, title))
    return results


def _find_labeled_text(soup: BeautifulSoup, label: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(label)}\s*[:：]?\s*(.+?)\s*$", re.I)
    for tag in soup.find_all(["li", "p", "div", "td", "span"]):
        text = _clean(tag.get_text(" ", strip=True))
        match = pattern.match(text)
        if match:
            value = _clean(match.group(1))
            if value:
                return value
    return None


def _title_from_soup(soup: BeautifulSoup) -> str:
    for tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        for tag in soup.find_all(tag_name):
            text = _clean(tag.get_text(" ", strip=True))
            if text and "WEVITY" not in text.upper() and len(text) >= 4:
                return text
    if soup.title:
        text = _clean(soup.title.get_text(" ", strip=True))
        text = re.sub(r"\s*[-|]\s*WEVITY.*$", "", text, flags=re.I)
        return text
    return ""


def _parse_date_pair(value: str | None):
    if not value:
        return None, None, None
    dates = re.findall(r"(20\d{2})[.\-/\s]+(\d{1,2})[.\-/\s]+(\d{1,2})", value)
    parsed = []
    for year, month, day in dates[:2]:
        try:
            parsed.append(datetime(int(year), int(month), int(day)).date())
        except ValueError:
            pass
    start = parsed[0] if parsed else None
    end = parsed[1] if len(parsed) > 1 else (parsed[0] if len(parsed) == 1 else None)
    return start, end, value


def _category(raw: str | None, title: str) -> str | None:
    text = f"{raw or ''} {title}".lower()
    mappings = [
        (("ai", "데이터", "웹/모바일", "게임/소프트웨어"), "Data / AI"),
        (("과학/공학", "공학", "건축/건설"), "Engineering"),
        (("광고/마케팅", "마케팅", "광고"), "Marketing"),
        (("디자인", "캐릭터", "웹툰"), "Design"),
        (("취업/창업", "창업", "스타트업", "ir"), "Startup / Business"),
        (("기획/아이디어", "아이디어", "기획"), "Idea / Planning"),
        (("논문/리포트", "논문"), "Case / Research"),
        (("환경", "esg", "지속가능", "탄소"), "Sustainability"),
    ]
    for words, label in mappings:
        if any(word in text for word in words):
            return label
    return _clean(raw) or None


def is_relevant_title(title: str) -> bool:
    compact = _clean(title)
    if any(word in compact for word in COMPETITION_WORDS):
        return True
    if any(word in compact for word in EXCLUDE_ONLY_WORDS):
        return False
    return False


def parse_detail(
    detail_html: str,
    source_url: str,
    fetched_at: datetime | None = None,
    listing_title: str | None = None,
) -> CompetitionRecord:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    soup = BeautifulSoup(detail_html, "html.parser")
    # The WEVITY detail page contains shared navigation headings that can be
    # mistaken for the contest title. The listing page already exposes the
    # actual contest title, so prefer that stable value when available.
    title = _clean(listing_title) or _title_from_soup(soup)
    query = parse_qs(urlparse(source_url).query)
    external_id = (query.get("ix") or [""])[0]
    if not title or not external_id:
        raise ValueError("WEVITY detail is missing title or stable ix id")

    raw_category = _find_labeled_text(soup, "분야")
    eligibility = _find_labeled_text(soup, "응모대상")
    organizer = _find_labeled_text(soup, "주최/주관") or _find_labeled_text(soup, "주최사")
    period = _find_labeled_text(soup, "접수기간")
    start_date, deadline_date, original_deadline_text = _parse_date_pair(period)

    page_text = _clean(soup.get_text(" ", strip=True))
    today = datetime.now(KOREA_TZ).date()
    active = deadline_date is None or deadline_date >= today

    participation = None
    if "팀" in page_text and ("개인" in page_text or "1인" in page_text):
        participation = "Individual or team"
    elif "팀" in page_text:
        participation = "Team"
    elif "개인" in page_text or "1인" in page_text:
        participation = "Individual"

    return CompetitionRecord(
        name=title,
        organizer=organizer,
        deadline=deadline_date.isoformat() if deadline_date else None,
        deadline_date=deadline_date,
        description="See original competition page for details.",
        category=_category(raw_category, title),
        eligibility=eligibility,
        participation_type=participation,
        source_name=SOURCE_NAME,
        source_url=source_url,
        external_id=external_id,
        fetched_at=fetched_at,
        application_start_date=start_date,
        original_deadline_text=original_deadline_text,
        is_active=active,
    )


def fetch_competitions() -> tuple[list[CompetitionRecord], dict[str, int]]:
    fetched = parsed = skipped = errors = 0
    records: list[CompetitionRecord] = []
    fetched_at = datetime.now(timezone.utc)
    links: list[tuple[str, str]] = []
    seen_ids = set()

    for page in range(1, MAX_PAGES + 1):
        page_html = _request_text(LIST_URL.format(page=page))
        page_links = parse_listing_links(page_html)
        if not page_links:
            break
        for url, title in page_links:
            external_id = (parse_qs(urlparse(url).query).get("ix") or [""])[0]
            if not external_id or external_id in seen_ids:
                continue
            seen_ids.add(external_id)
            fetched += 1
            if not is_relevant_title(title):
                skipped += 1
                continue
            links.append((url, title))
            if len(links) >= MAX_DETAIL_REQUESTS:
                break
        if len(links) >= MAX_DETAIL_REQUESTS:
            break
        time.sleep(REQUEST_DELAY_SECONDS)

    for url, listing_title in links:
        try:
            detail_html = _request_text(url)
            record = parse_detail(
                detail_html,
                url,
                fetched_at=fetched_at,
                listing_title=listing_title,
            )
            if not is_relevant_title(record.name):
                skipped += 1
            else:
                records.append(record)
                parsed += 1
        except Exception:
            errors += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return records, {"fetched": fetched, "parsed": parsed, "skipped": skipped, "errors": errors}
