import re
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from apps.core.models import FamousAlumni, FamousAlumniCandidate, School

SECTION_KEYWORDS = ("출신 인물", "출신인물", "출신 유명인")
BLOCK_TAGS = {
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "li",
    "p",
    "td",
    "th",
    "tr",
}
SKIP_PREFIXES = (
    "관련 문서",
    "분류",
    "각주",
    "외부 링크",
    "둘러보기",
    "참고",
    "더 보기",
    "namu.wiki",
)
SKIP_CONTAINS = (
    "나무위키에 등재",
    "가나다순",
    "이름 - 직업",
    "정렬합니다",
    "재학한 사실",
    "상위 문서",
    "최근 수정 시각",
    "편집 요청",
    "해당 문단은",
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return unescape("".join(self.parts))


def clean_line(line: str) -> str:
    line = re.sub(r"\[[^\]]+\]", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" \t\r\n-•·")


def normalize_heading(line: str) -> str:
    return re.sub(r"[\s.0-9#]+", "", line)


def looks_like_next_section(line: str) -> bool:
    return bool(re.match(r"^\d+(\.\d+)*\.\s+\S+", line))


def looks_like_toc_line(line: str) -> bool:
    return len(re.findall(r"\d+\.", line)) > 1


def extract_section_lines(text: str) -> list[str]:
    lines = [clean_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    is_alumni_subpage = any("/출신 인물" in line for line in lines[:10])
    start_index = None
    keyword_norms = {keyword.replace(" ", "") for keyword in SECTION_KEYWORDS}
    for index, line in enumerate(lines):
        normalized = normalize_heading(line)
        if normalized not in keyword_norms:
            continue
        if not is_alumni_subpage and not looks_like_next_section(line):
            continue
        if looks_like_toc_line(line):
            continue
        if normalized in keyword_norms:
            start_index = index + 1
            break

    if start_index is None:
        return []

    if is_alumni_subpage:
        for index in range(start_index, len(lines)):
            if looks_like_next_section(lines[index]) and not looks_like_toc_line(lines[index]):
                start_index = index
                break

    section_lines: list[str] = []
    for line in lines[start_index:]:
        if looks_like_next_section(line) and not is_alumni_subpage:
            break
        if is_alumni_subpage and looks_like_next_section(line) and "가상 인물" in line:
            break
        if any(line.startswith(prefix) for prefix in SKIP_PREFIXES):
            break
        section_lines.append(line)
    return section_lines


def candidate_from_line(line: str) -> tuple[str, str] | None:
    line = clean_line(line)
    if not line or len(line) > 180:
        return None
    if looks_like_next_section(line):
        return None
    if any(phrase in line for phrase in SKIP_CONTAINS):
        return None
    if re.search(r"(합니다|하십시오|바랍니다|기재)$", line):
        return None
    if any(keyword.replace(" ", "") in normalize_heading(line) for keyword in SECTION_KEYWORDS):
        return None

    name_part = re.split(r"\s[-–—:：]\s| - | – | — |:", line, maxsplit=1)[0]
    name_part = re.sub(r"\(.+?\)", "", name_part).strip()
    name_part = re.sub(r"\s+", " ", name_part)

    if not (2 <= len(name_part) <= 40):
        return None
    if not re.search(r"[가-힣A-Za-z]", name_part):
        return None
    if name_part.startswith(SKIP_PREFIXES):
        return None

    description = line
    if description == name_part:
        description = ""
    return name_part, description[:255]


def extract_candidates(html: str) -> list[tuple[str, str, str]]:
    parser = TextExtractor()
    parser.feed(html)
    section_lines = extract_section_lines(parser.text())

    candidates: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for line in section_lines:
        candidate = candidate_from_line(line)
        if not candidate:
            continue
        name, description = candidate
        if name in seen:
            continue
        seen.add(name)
        candidates.append((name, description, line))
    return candidates


class Command(BaseCommand):
    help = "Crawl a Namuwiki school page and save famous alumni candidates for admin review."

    def add_arguments(self, parser: CommandParser) -> None:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--all", action="store_true", help="Crawl every registered school.")
        group.add_argument("--school-code")
        group.add_argument("--school-name")
        parser.add_argument("--url", help="Namuwiki page URL. Defaults to the school name page.")
        parser.add_argument("--timeout", type=int, default=15)
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of schools to crawl with --all.",
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--auto-approve",
            action="store_true",
            help="Immediately publish crawled candidates as visible famous alumni.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["all"]:
            if options["url"]:
                raise RuntimeError("--url can only be used with one school.")
            self.handle_all(options)
            return

        school = self.get_school(options)
        result = self.crawl_school(school, options)
        self.write_result(result, options)

    def handle_all(self, options: dict[str, Any]) -> None:
        schools = School.objects.filter(is_closed=False).order_by("name")
        if options["limit"]:
            schools = schools[: options["limit"]]

        total_created = 0
        total_skipped = 0
        total_approved = 0
        total_found_schools = 0
        total_empty_schools = 0
        total_failed_schools = 0

        for index, school in enumerate(schools, start=1):
            self.write_line(f"[{index}] {school.name} crawling...")
            try:
                result = self.crawl_school(school, options)
            except RuntimeError as exc:
                total_failed_schools += 1
                self.write_line(f"  skipped: {exc}")
                continue

            if result["candidate_count"] == 0:
                total_empty_schools += 1
                self.write_line("  no candidates")
                continue

            total_found_schools += 1
            total_created += result["created_count"]
            total_skipped += result["skipped_count"]
            total_approved += result["approved_count"]
            self.write_line(
                "  found="
                f"{result['candidate_count']}, created={result['created_count']}, "
                f"skipped={result['skipped_count']}, approved={result['approved_count']}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Finished all-school crawl. "
                f"found_schools={total_found_schools}, empty_schools={total_empty_schools}, "
                f"failed_schools={total_failed_schools}, created={total_created}, "
                f"skipped={total_skipped}, approved={total_approved}"
            )
        )

    def crawl_school(self, school: School, options: dict[str, Any]) -> dict[str, int]:
        source_url, html = self.fetch_school_page(school, options)
        candidates = extract_candidates(html)

        if not candidates:
            return {
                "candidate_count": 0,
                "created_count": 0,
                "skipped_count": 0,
                "approved_count": 0,
            }

        created_count = 0
        skipped_count = 0
        approved_count = 0
        for name, description, raw_text in candidates:
            if options["dry_run"]:
                self.write_line(f"{name} | {description}")
                continue

            candidate, created = FamousAlumniCandidate.objects.get_or_create(
                school=school,
                name=name,
                source_url=source_url,
                defaults={
                    "description": description,
                    "source_name": "나무위키",
                    "raw_text": raw_text,
                },
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1
            if options["auto_approve"] and self.approve_candidate(candidate):
                approved_count += 1

        return {
            "candidate_count": len(candidates),
            "created_count": created_count,
            "skipped_count": skipped_count,
            "approved_count": approved_count,
        }

    def write_result(self, result: dict[str, int], options: dict[str, Any]) -> None:
        if result["candidate_count"] == 0:
            self.stdout.write(self.style.WARNING("No alumni candidates found."))
            return

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Found {result['candidate_count']} candidates."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Saved alumni candidates. "
                    f"created={result['created_count']}, skipped={result['skipped_count']}, "
                    f"approved={result['approved_count']}"
                )
            )

    def get_school(self, options: dict[str, Any]) -> School:
        if options["school_code"]:
            return School.objects.get(code=options["school_code"])
        return School.objects.get(name=options["school_name"])

    def fetch(self, url: str, timeout: int) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": "dongmoon/0.1 alumni candidate collector",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc

    def fetch_school_page(self, school: School, options: dict[str, Any]) -> tuple[str, str]:
        if options["url"]:
            return options["url"], self.fetch(options["url"], options["timeout"])

        urls = [
            f"https://namu.wiki/w/{quote(f'{school.name}/출신 인물')}",
            f"https://namu.wiki/w/{quote(school.name)}",
        ]
        last_error = None
        for url in urls:
            try:
                return url, self.fetch(url, options["timeout"])
            except RuntimeError as exc:
                last_error = exc
        raise RuntimeError(f"Failed to fetch Namuwiki pages for {school.name}: {last_error}")

    def approve_candidate(self, candidate: FamousAlumniCandidate) -> bool:
        if candidate.status == candidate.Status.APPROVED and candidate.approved_alumni_id:
            return False

        alumni, _ = FamousAlumni.objects.get_or_create(
            school=candidate.school,
            name=candidate.name,
            source_url=candidate.source_url,
            defaults={
                "description": candidate.description,
                "source_name": candidate.source_name,
                "verified_at": timezone.now(),
                "is_visible": True,
            },
        )
        if not alumni.is_visible:
            alumni.is_visible = True
            alumni.save(update_fields=["is_visible", "updated_at"])

        candidate.status = candidate.Status.APPROVED
        candidate.reviewed_at = timezone.now()
        candidate.approved_alumni = alumni
        candidate.save(update_fields=["status", "reviewed_at", "approved_alumni", "updated_at"])
        return True

    def write_line(self, message: str) -> None:
        safe_message = message.encode("cp949", errors="replace").decode("cp949")
        self.stdout.write(safe_message)
