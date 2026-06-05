import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dotenv import load_dotenv

load_dotenv(REPO / ".env")

import sources
from scrub import scrub_text
from app.rag import Store

RESUME = "Anisha_resume.pdf"
INTERVIEW_PDFS = ["pulse-interview.pdf", "recommendation interview.pdf"]
SUMMARIES = REPO / "knowledge" / "repo_summaries"


def chunk_text(text, size=1800, overlap=200):
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def add(chunks, text, source, repo, url, tier, size=1800):
    for piece in chunk_text(text, size=size):
        clean, _ = scrub_text(piece)
        chunks.append({
            "id": f"{source}#{len(chunks)}",
            "text": clean,
            "source": source,
            "repo": repo,
            "url": url,
            "tier": tier,
        })


def collect():
    chunks = []

    add(chunks, sources.read_pdf(REPO / RESUME), "resume", "", "", 1, size=700)

    for name in INTERVIEW_PDFS:
        path = REPO / name
        if path.exists():
            add(chunks, sources.read_pdf(path), name.replace(".pdf", ""), "", "", 1)

    if SUMMARIES.exists():
        for card in SUMMARIES.glob("*.md"):
            text = card.read_text(encoding="utf-8")
            if text.lower().count("not documented") >= 3:
                continue
            add(chunks, text, f"summary:{card.stem}", card.stem, "", 1)

    repos = sources.list_repos()
    print(f"Found {len(repos)} repos")
    for repo in repos:
        name, branch, url = repo["name"], repo["branch"], repo["url"]
        print(f"  {name}")

        rm = sources.readme(name, branch)
        if rm:
            add(chunks, rm, f"readme:{name}", name, url, 1)
        if repo["description"]:
            add(chunks, repo["description"], f"about:{name}", name, url, 1)

        for path, body in sources.docs(name, branch):
            add(chunks, body, f"doc:{name}/{path}", name, url, 1)

        msgs = sources.commit_messages(name)
        if msgs:
            add(chunks, "\n".join(msgs), f"commits:{name}", name, url, 2)

        for path, body in sources.code_files(name, branch):
            add(chunks, body, f"code:{name}/{path}", name, f"{url}/blob/{branch}/{path}", 3)

    return chunks


def main():
    chunks = collect()
    by_tier = {t: sum(1 for c in chunks if c["tier"] == t) for t in (1, 2, 3)}
    print(f"\n{len(chunks)} chunks  (tier1={by_tier[1]} tier2={by_tier[2]} tier3={by_tier[3]})")
    print("Embedding...")
    Store.build(chunks)
    print(f"Stored -> {REPO / 'data'}")


if __name__ == "__main__":
    main()
