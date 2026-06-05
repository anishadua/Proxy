import os
from pathlib import Path

import httpx
from pypdf import PdfReader

USER = os.getenv("GITHUB_USERNAME", "anishadua")
TOKEN = os.getenv("GITHUB_TOKEN")
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java"}
SKIP = ("node_modules", "dist/", "build/", ".min.", "vendor/", "package-lock", ".lock")
SKIP_REPOS = {"Proxy"}


def _headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": "proxy-ingest"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def _get(url, **kw):
    return httpx.get(url, headers=_headers(), timeout=30, **kw)


def list_repos():
    r = _get(f"{API}/users/{USER}/repos", params={"per_page": 100, "type": "owner", "sort": "updated"})
    r.raise_for_status()
    repos = []
    for repo in r.json():
        if repo["fork"] or repo["name"] in SKIP_REPOS:
            continue
        repos.append({
            "name": repo["name"],
            "branch": repo["default_branch"],
            "description": repo.get("description") or "",
            "url": repo["html_url"],
        })
    return repos


def readme(repo, branch):
    for fname in ("README.md", "readme.md", "README.MD", "README.rst", "README"):
        r = httpx.get(f"{RAW}/{USER}/{repo}/{branch}/{fname}", timeout=30)
        if r.status_code == 200 and r.text.strip():
            return r.text
    return ""


def commit_messages(repo):
    r = _get(f"{API}/repos/{USER}/{repo}/commits", params={"per_page": 100})
    if r.status_code != 200:
        return []
    return [c["commit"]["message"].strip() for c in r.json() if c["commit"]["message"].strip()]


def _tree(repo, branch):
    r = _get(f"{API}/repos/{USER}/{repo}/git/trees/{branch}", params={"recursive": 1})
    if r.status_code != 200:
        return []
    return r.json().get("tree", [])


def docs(repo, branch, limit=5):
    out = []
    for node in _tree(repo, branch):
        path = node.get("path", "")
        if node.get("type") != "blob" or not path.lower().endswith(".md"):
            continue
        if path.lower().endswith("readme.md") or any(s in path.lower() for s in SKIP):
            continue
        r = httpx.get(f"{RAW}/{USER}/{repo}/{branch}/{path}", timeout=30)
        if r.status_code == 200 and r.text.strip():
            out.append((path, r.text))
        if len(out) == limit:
            break
    return out


def code_files(repo, branch, limit=15):
    blobs = [
        n for n in _tree(repo, branch)
        if n.get("type") == "blob"
        and Path(n["path"]).suffix in CODE_EXT
        and n.get("size", 0) < 40000
        and not any(s in n["path"].lower() for s in SKIP)
    ]
    blobs.sort(key=lambda n: n.get("size", 0), reverse=True)
    out = []
    for node in blobs[:limit]:
        path = node["path"]
        r = httpx.get(f"{RAW}/{USER}/{repo}/{branch}/{path}", timeout=30)
        if r.status_code == 200 and r.text.strip():
            out.append((path, r.text))
    return out


def read_pdf(path):
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
