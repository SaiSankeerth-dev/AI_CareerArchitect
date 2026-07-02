import re
from pathlib import Path

from app.collectors.base import BaseCollector, CollectedData, CollectorError

SECTION_HEADERS = {
    "skills": re.compile(r"^\s*(technical\s+)?skills?\b", re.IGNORECASE),
    "experience": re.compile(r"^\s*(work\s+|professional\s+)?experience\b", re.IGNORECASE),
    "education": re.compile(r"^\s*education\b", re.IGNORECASE),
    "projects": re.compile(r"^\s*projects?\b", re.IGNORECASE),
    "certifications": re.compile(r"^\s*certifications?\b", re.IGNORECASE),
    "summary": re.compile(r"^\s*(summary|objective|profile)\b", re.IGNORECASE),
}


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "header"
    for line in text.splitlines():
        matched = None
        for name, pattern in SECTION_HEADERS.items():
            if pattern.match(line) and len(line.strip()) < 40:
                matched = name
                break
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


class ResumeCollector(BaseCollector):
    """Parses PDF/DOCX resumes fully locally — no cloud service, no cost."""

    platform = "resume"

    async def collect(self, url_or_path: str) -> CollectedData:
        path = Path(url_or_path)
        if not path.exists():
            raise CollectorError(f"Resume file not found: {url_or_path}")
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text = self._read_pdf(path)
        elif suffix in (".docx", ".doc"):
            text = self._read_docx(path)
        elif suffix in (".txt", ".md"):
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            raise CollectorError(f"Unsupported resume format: {suffix}")
        sections = split_sections(text)
        return CollectedData(
            platform=self.platform,
            url=str(path),
            text=text,
            metadata={"filename": path.name, "sections_found": list(sections)},
            items=[{"type": "section", "name": name, "content": content}
                   for name, content in sections.items() if content],
        )

    @staticmethod
    def _read_pdf(path: Path) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    @staticmethod
    def _read_docx(path: Path) -> str:
        import docx

        document = docx.Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
