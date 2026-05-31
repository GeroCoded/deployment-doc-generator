"""Collects deterministic facts from local git clones: commits, stat, diff, links.

Pure stdlib + git CLI. No docx/xlsx deps here so it stays easy to test and reuse
(e.g. from the future CLI). Fails LOUDLY when a tag is missing rather than emitting
an empty/misleading diff into a deployment document.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional


class GitCollectorError(RuntimeError):
    pass


@dataclass
class Commit:
    short_hash: str
    subject: str
    author: str


@dataclass
class RepoChanges:
    name: str
    prod_tag: str
    deploy_tag: str
    tag_url_prod: str
    tag_url_deploy: str
    compare_url: str
    commits: list[Commit] = field(default_factory=list)
    stat: str = ""
    diff: str = ""
    diff_truncated: bool = False


def _git(path: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", path, *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GitCollectorError(
            f"git {' '.join(args)} failed in {path!r}:\n{proc.stderr.strip()}"
        )
    return proc.stdout


def _tag_exists(path: str, ref: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", path, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def resolve_repo_path(name: str, explicit_path: Optional[str], repos_root: Optional[str]) -> str:
    """Return a usable local path for a repo.

    Priority: explicit `path` in the manifest, else `<repos_root>/<name>`.
    This is what makes the future 'repos_root' preference (Q-B) a drop-in.
    """
    candidates = []
    if explicit_path:
        candidates.append(os.path.expanduser(explicit_path))
    if repos_root:
        candidates.append(os.path.join(os.path.expanduser(repos_root), name))
    for c in candidates:
        if os.path.isdir(os.path.join(c, ".git")):
            return c
    raise GitCollectorError(
        f"Could not locate a git clone for repo {name!r}. Tried: {candidates or '(nothing — set path or repos_root)'}"
    )


def build_urls(github_base: str, org: str, name: str, repo_url: Optional[str],
               prod_tag: str, deploy_tag: str) -> tuple[str, str, str]:
    base = (repo_url or "/".join(p for p in [github_base.rstrip("/"), org] if p) + f"/{name}").rstrip("/")
    tag_url_prod = f"{base}/releases/tag/{prod_tag}"
    tag_url_deploy = f"{base}/releases/tag/{deploy_tag}"
    compare_url = f"{base}/compare/{prod_tag}...{deploy_tag}"
    return tag_url_prod, tag_url_deploy, compare_url


def collect_repo(*, name: str, prod_tag: str, deploy_tag: str, path: str,
                 github_base: str, org: str, repo_url: Optional[str] = None,
                 fetch: bool = True, exclude: Optional[list[str]] = None,
                 max_diff_lines: int = 4000) -> RepoChanges:
    if fetch:
        # Best-effort; an offline/locked VDI may block this. Never fatal.
        try:
            _git(path, "fetch", "--tags", "--quiet")
        except GitCollectorError:
            pass

    for tag in (prod_tag, deploy_tag):
        if not _tag_exists(path, tag):
            raise GitCollectorError(
                f"[{name}] tag {tag!r} not found in {path}. "
                f"Fetch tags or fix the manifest — refusing to emit an empty diff."
            )

    rng = f"{prod_tag}..{deploy_tag}"
    tag_url_prod, tag_url_deploy, compare_url = build_urls(
        github_base, org, name, repo_url, prod_tag, deploy_tag
    )

    log_raw = _git(path, "log", "--pretty=format:%h\x1f%s\x1f%an", rng)
    commits = []
    for line in log_raw.splitlines():
        if not line.strip():
            continue
        h, s, a = line.split("\x1f")
        commits.append(Commit(short_hash=h, subject=s, author=a))

    pathspec = []
    if exclude:
        pathspec = ["--", "."] + [f":(exclude){p}" for p in exclude]

    stat = _git(path, "diff", "--stat", rng, *pathspec).rstrip()
    diff_full = _git(path, "diff", rng, *pathspec)

    diff_lines = diff_full.splitlines()
    truncated = False
    if len(diff_lines) > max_diff_lines:
        diff_lines = diff_lines[:max_diff_lines]
        diff_lines.append(
            f"... [diff truncated at {max_diff_lines} lines — see the full comparison link above]"
        )
        truncated = True

    return RepoChanges(
        name=name,
        prod_tag=prod_tag,
        deploy_tag=deploy_tag,
        tag_url_prod=tag_url_prod,
        tag_url_deploy=tag_url_deploy,
        compare_url=compare_url,
        commits=commits,
        stat=stat,
        diff="\n".join(diff_lines),
        diff_truncated=truncated,
    )
