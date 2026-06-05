import re
import sys
from pathlib import Path

from pypdf import PdfReader

REPO = Path(__file__).resolve().parent.parent

SENSITIVE_DOCS = ["pulse-interview.pdf", "recommendation interview.pdf"]

PATTERNS = [
    ("phone", re.compile(r"(?:\+?91[\s\-]?)?[6-9]\d{9}")),
    ("email", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("internal_host", re.compile(r"\b[a-z0-9-]+\.adda247\.com[^\s)\"']*", re.I)),
    ("collection", re.compile(r"Adda247 RAG data [\d.]+ - [A-Za-z ]+")),
    ("bq_table", re.compile(r"\bpulse\.[a-z_]+\b")),
]

LITERALS = [
    "adda247-dev",
    "event_analytics_staging",
    "speech_analytics_staging",
    "ai-crm-conversations",
    "/ML/ai-crm/config",
    "X-Auth-Token",
    "Redash",
]

PLACEHOLDER = "[redacted]"


def scrub_text(text):
    hits = {}
    for name, pat in PATTERNS:
        text, n = pat.subn(PLACEHOLDER, text)
        if n:
            hits[name] = hits.get(name, 0) + n
    for lit in LITERALS:
        n = text.count(lit)
        if n:
            text = text.replace(lit, PLACEHOLDER)
            hits["literal:" + lit] = n
    return text, hits


def read_pdf(path):
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def main():
    report = ["Scrub report — redactions applied before embedding\n"]
    total = 0
    for name in SENSITIVE_DOCS:
        path = REPO / name
        if not path.exists():
            report.append(f"{name}: MISSING\n")
            continue
        _, hits = scrub_text(read_pdf(path))
        count = sum(hits.values())
        total += count
        report.append(f"{name}: {count} redactions")
        for k, v in sorted(hits.items()):
            report.append(f"    {k}: {v}")
        report.append("")
    report.append(f"TOTAL: {total} redactions")
    out = "\n".join(report)
    (REPO / "scrub_report.txt").write_text(out, encoding="utf-8")
    print(out)
    if total == 0:
        print("\nWARNING: nothing was redacted — check patterns.", file=sys.stderr)


if __name__ == "__main__":
    main()
