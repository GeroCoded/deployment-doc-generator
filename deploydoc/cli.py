"""Entry point: python -m deploydoc generate --manifest deployment.yml --out ./out

Reads the manifest, collects git facts for each repo, and emits the three
documents. Designed to run inside the locked VDI where the repos live.
"""
from __future__ import annotations

import argparse
import os
import sys

import yaml

from .git_collector import GitCollectorError, collect_repo, resolve_repo_path
from .render_docx import render_code_comparison, render_technical_summary
from .render_xlsx import render_change_request

DEFAULT_TEMPLATES = {
    "technical_summary": "templates/technical_summary_template.docx",
    "code_comparison": "templates/code_comparison_template.docx",
    "change_request": "templates/change_request_template.xlsx",
}


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _scan_todos(manifest: dict) -> list[str]:
    """Flag any human field the manifest author (or Rovo) left as TODO."""
    todos: list[str] = []

    def walk(node, trail):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{trail}.{k}" if trail else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{trail}[{i}]")
        elif isinstance(node, str) and node.strip().upper().startswith("TODO"):
            todos.append(trail)

    walk(manifest, "")
    return todos


def cmd_generate(args: argparse.Namespace) -> int:
    manifest = _load_yaml(args.manifest)
    cr = manifest.get("change_request")
    if not cr:
        print("ERROR: manifest has no top-level 'change_request' key", file=sys.stderr)
        return 2

    prefs = _load_yaml(args.prefs) if args.prefs and os.path.exists(args.prefs) else {}
    repos_root = prefs.get("repos_root") or cr.get("repos_root")
    github_base = cr.get("github_base", prefs.get("github_base", ""))
    org = cr.get("org", prefs.get("org", ""))
    exclude = cr.get("exclude", prefs.get("exclude", []))
    max_diff_lines = int(cr.get("max_diff_lines", prefs.get("max_diff_lines", 4000)))
    fetch = not args.no_fetch

    todos = _scan_todos(manifest)
    if todos:
        print("NOTE: the following fields are still TODO (will appear literally in the docs):")
        for t in todos:
            print(f"  - {t}")
        print()

    os.makedirs(args.out, exist_ok=True)

    # --- collect git facts per repo ---
    repo_changes = []
    for repo in cr.get("repos", []):
        try:
            path = resolve_repo_path(repo["name"], repo.get("path"), repos_root)
            rc = collect_repo(
                name=repo["name"],
                prod_tag=repo["prod_tag"],
                deploy_tag=repo["deploy_tag"],
                path=path,
                github_base=github_base,
                org=org,
                repo_url=repo.get("repo_url"),
                fetch=fetch,
                exclude=exclude,
                max_diff_lines=max_diff_lines,
            )
            repo_changes.append(rc)
            flag = " (diff truncated)" if rc.diff_truncated else ""
            print(f"  collected {repo['name']}: {len(rc.commits)} commits{flag}")
        except GitCollectorError as e:
            print(f"ERROR collecting {repo.get('name', '?')}: {e}", file=sys.stderr)
            if args.strict:
                return 1

    templates = {**DEFAULT_TEMPLATES}
    for key in templates:
        override = getattr(args, key, None)
        if override:
            templates[key] = override

    # --- render ---
    ts_out = os.path.join(args.out, "Technical Summary.docx")
    cc_out = os.path.join(args.out, "Code Comparison.docx")
    crq_out = os.path.join(args.out, "Change Request.xlsx")

    render_technical_summary(manifest, templates["technical_summary"], ts_out)
    print(f"  wrote {ts_out}")

    render_code_comparison(manifest, repo_changes, templates["code_comparison"], cc_out)
    print(f"  wrote {cc_out}")

    warnings = render_change_request(manifest, templates["change_request"], crq_out)
    print(f"  wrote {crq_out}")
    for w in warnings:
        print(f"  XLSX WARNING: {w}", file=sys.stderr)

    print("\nDone.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="deploydoc")
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate the three deployment documents")
    g.add_argument("--manifest", required=True, help="path to deployment.yml")
    g.add_argument("--out", default="out", help="output directory")
    g.add_argument("--prefs", default="deploydoc.prefs.yml", help="optional user preferences file")
    g.add_argument("--technical_summary", help="override template path")
    g.add_argument("--code_comparison", help="override template path")
    g.add_argument("--change_request", help="override template path")
    g.add_argument("--no-fetch", action="store_true", help="skip 'git fetch --tags'")
    g.add_argument("--strict", action="store_true", help="abort if any repo fails to collect")
    g.set_defaults(func=cmd_generate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
