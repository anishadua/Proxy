import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dotenv import load_dotenv

load_dotenv(REPO / ".env")

import sources
from app import llm

OUT = REPO / "knowledge" / "repo_summaries"

PROMPT = """You are summarising one of Anisha's GitHub repos for her interview persona. \
Use ONLY the README and commit messages below — do not invent anything. If a field is not \
covered by the material, write "not documented".

Write a short card with these headings exactly:
Purpose:
Tech stack:
Architecture:
Design tradeoffs:
What she'd do differently / future work:

REPO: {name}
DESCRIPTION: {desc}

README:
{readme}

RECENT COMMITS:
{commits}"""


def card(repo):
    name, branch = repo["name"], repo["branch"]
    readme = sources.readme(name, branch)[:6000]
    commits = "\n".join(sources.commit_messages(name)[:40])[:2000]
    if not readme and not commits:
        return None
    messages = [{"role": "user", "content": PROMPT.format(
        name=name, desc=repo["description"], readme=readme or "none", commits=commits or "none")}]
    return llm.complete(messages, temperature=0.2, max_tokens=700)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for repo in sources.list_repos():
        text = card(repo)
        if text:
            (OUT / f"{repo['name']}.md").write_text(text, encoding="utf-8")
            print(f"  wrote {repo['name']}.md")
        else:
            print(f"  skipped {repo['name']} (no readme/commits)")


if __name__ == "__main__":
    main()
