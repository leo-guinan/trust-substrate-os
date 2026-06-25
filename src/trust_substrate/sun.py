"""
Generate a sun descriptor from a local repository.

The sun represents the corpus of work: its mass comes from file volume,
word count, commit density, and recency.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, List


@dataclass(frozen=True)
class SunDescriptor:
    id: str
    name: str
    display_name: str
    description: str
    mass: float
    color: str
    emissions: list[str]
    bonds: list[dict[str, Any]]
    last_commit: str | None
    file_count: int
    word_count: int
    commit_count: int
    active_days: int


IGNORE_DIRS = {".git", "node_modules", "dist", "build", "__pycache__", ".next", ".venv", "venv"}
CODE_EXTS = {".py", ".rs", ".go", ".js", ".ts", ".jsx", ".tsx", ".rb", ".java", ".c", ".cpp", ".h", ".md", ".json", ".yaml", ".yml", ".toml", ".txt"}
LANG_COLORS = {
    "python": "#3572A5",
    "rust": "#dea584",
    "go": "#00ADD8",
    "javascript": "#f1e05a",
    "typescript": "#3178c6",
    "ruby": "#701516",
    "java": "#b07219",
    "markdown": "#083fa1",
    "json": "#292929",
}


def _git(repo: Path, *args: str) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL, text=True
        )
        return out.strip()
    except subprocess.CalledProcessError:
        return None


def _collect_word_counts(repo: Path):
    total = 0
    files = 0
    by_ext: dict[str, int] = {}
    for root, dirs, files_iter in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fn in files_iter:
            p = Path(root, fn)
            ext = p.suffix.lower()
            if ext not in CODE_EXTS:
                continue
            files += 1
            try:
                text = p.read_text(errors="ignore")
                words = len(re.findall(r"\b\w+\b", text))
            except Exception:
                words = 0
            total += words
            by_ext[ext] = by_ext.get(ext, 0) + 1
    return total, by_ext, files


def _detect_remote(repo: Path) -> dict[str, Any] | None:
    url = _git(repo, "remote", "get-url", "origin")
    if not url:
        return None
    m = re.search(r"github.com[:/]+([^/]+)/([^/.]+)", url)
    if not m:
        return None
    owner, name = m.group(1), m.group(2)
    return {"name": f"{owner}/{name}", "owner": owner, "repo": name, "url": url}


def _dominant_language(by_ext: dict[str, int]) -> tuple[str, str]:
    if not by_ext:
        return "unknown", "#9ca3af"
    ext = max(by_ext, key=by_ext.get)
    mapping = {
        ".py": "python",
        ".rs": "rust",
        ".go": "go",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".rb": "ruby",
        ".java": "java",
        ".md": "markdown",
        ".json": "json",
    }
    lang = mapping.get(ext, ext.lstrip("."))
    return lang, LANG_COLORS.get(lang, "#9ca3af")


def scan_repo(repo_path: str | Path) -> SunDescriptor:
    repo = Path(repo_path).resolve()
    if not repo.exists() or not (repo / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo}")

    name = repo.name
    display_name = name.replace("-", " ").replace("_", " ").title()

    readme = (repo / "README.md")
    description = readme.read_text(errors="ignore").splitlines()[0].strip() if readme.exists() else f"Corpus repository: {name}"

    word_count, by_ext, file_count = _collect_word_counts(repo)
    lang, color = _dominant_language(by_ext)

    log = _git(repo, "log", "--format=%H %ai", "--no-merges") or ""
    lines = [ln.strip() for ln in log.splitlines() if ln.strip()]
    commits = len(lines)
    active_days = len({ln.split()[1][:10] for ln in lines if len(ln.split()) > 1})
    last_commit = lines[-1].split()[1] if lines else None

    # mass: composite score; cap and scale for visual size
    mass = min(48.0, 6.0 + (file_count / 300) + (commits / 50) + (active_days / 10))

    # emissions: simple heuristic keywords from description + inferred topic
    emissions: list[str] = []
    raw_tokens = re.findall(r"\b[A-Za-z]{3,}\b", description + " " + name)
    for token in raw_tokens:
        low = token.lower()
        if low in {"the", "and", "for", "with", "from", "this", "that", "public", "archive", "dataset"}:
            continue
        emissions.append(token.title())
    # de-duplicate and keep compact
    seen: set[str] = set()
    uniq: list[str] = []
    for e in emissions:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    emissions = uniq[:5]
    if not emissions:
        emissions = [name, lang]

    # sun color: data-heavy repos get a warm amber; code-heavy get language color
    if ".json" in by_ext or ".csv" in by_ext:
        color = "#f59e0b"
    elif ".md" in by_ext and file_count < 20:
        color = "#fbbf24"

    bond = _detect_remote(repo)
    bonds = [{"name": bond["name"], "strength": 0.8}] if bond else []

    sun_id = f"sun_{re.sub(r'[^a-z0-9]+','_',name.lower()).strip('_')}"

    return SunDescriptor(
        id=sun_id,
        name=display_name,
        display_name=display_name,
        description=description,
        mass=mass,
        color=color,
        emissions=emissions,
        bonds=bonds,
        last_commit=last_commit,
        file_count=file_count,
        word_count=word_count,
        commit_count=commits,
        active_days=active_days,
    )


def to_json(sun: SunDescriptor) -> str:
    return json.dumps(asdict(sun), indent=2)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    print(to_json(scan_repo(path)))
