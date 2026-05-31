"""Renders the two Word documents (Technical Summary, Code Comparison) from a
manifest + collected git facts, using docxtpl so the company-branded template
is preserved and only placeholders are filled.
"""
from __future__ import annotations

from typing import Iterable

from docxtpl import DocxTemplate, RichText

from .git_collector import RepoChanges

# Diff line colors (hex, no '#').
C_FILE = "808080"   # diff --git / index / +++ / --- / new file ...
C_HUNK = "0B7285"   # @@ ... @@
C_ADD = "2F9E44"    # +added
C_DEL = "E03131"    # -removed
C_CTX = "000000"    # context
DIFF_FONT = "Consolas"
DIFF_SIZE = 16      # docxtpl RichText size is in half-points -> 8pt


def join_ticket_ids(ids: list[str]) -> str:
    if not ids:
        return ""
    if len(ids) == 1:
        return ids[0]
    return ", ".join(ids[:-1]) + " && " + ids[-1]


def _diff_line_color(line: str) -> str:
    if line.startswith(("diff --git", "index ", "--- ", "+++ ",
                        "new file", "deleted file", "rename ", "similarity ")):
        return C_FILE
    if line.startswith("@@"):
        return C_HUNK
    if line.startswith("+"):
        return C_ADD
    if line.startswith("-"):
        return C_DEL
    return C_CTX


def diff_to_richtext(diff: str) -> RichText:
    rt = RichText()
    lines = diff.splitlines() or ["(no textual changes)"]
    for line in lines:
        rt.add(line + "\n", color=_diff_line_color(line), font=DIFF_FONT, size=DIFF_SIZE)
    return rt


def link(tpl: DocxTemplate, text: str, url: str) -> RichText:
    rt = RichText()
    rt.add(text, url_id=tpl.build_url_id(url), color="0563C1", underline=True)
    return rt


def commits_to_richtext(commits: Iterable) -> RichText:
    rt = RichText()
    any_commit = False
    for c in commits:
        any_commit = True
        rt.add(f"{c.short_hash}  ", color="808080", font=DIFF_FONT, size=18)
        rt.add(f"{c.subject} ", size=18)
        rt.add(f"({c.author})\n", color="808080", italic=True, size=18)
    if not any_commit:
        rt.add("(no commits between these tags)", italic=True, color="808080")
    return rt


def render_technical_summary(manifest: dict, template_path: str, out_path: str) -> None:
    tpl = DocxTemplate(template_path)
    cr = manifest["change_request"]
    tickets = cr.get("tickets", [])
    context = {
        "ticket_ids": join_ticket_ids([t["id"] for t in tickets]),
        "deploy_date": cr.get("deploy_date", ""),
        "cr_number": cr.get("cr_number", ""),
        "tickets": tickets,
    }
    # autoescape=True is REQUIRED: it escapes &/</> in plain fields AND lets RichText
    # render without dropping content. With it off, '&' and '<...>' silently vanish.
    tpl.render(context, autoescape=True)
    tpl.save(out_path)


def render_code_comparison(manifest: dict, repo_changes: list[RepoChanges],
                           template_path: str, out_path: str) -> None:
    tpl = DocxTemplate(template_path)
    cr = manifest["change_request"]
    repos_ctx = []
    for rc in repo_changes:
        repos_ctx.append({
            "name": rc.name,
            "prod_tag": rc.prod_tag,
            "deploy_tag": rc.deploy_tag,
            "deploy_link": link(tpl, rc.deploy_tag, rc.tag_url_deploy),
            "prod_link": link(tpl, rc.prod_tag, rc.tag_url_prod),
            "compare_link": link(tpl, "GitHub comparison", rc.compare_url),
            "stat": rc.stat,
            "commits_rich": commits_to_richtext(rc.commits),
            "diff_rich": diff_to_richtext(rc.diff),
        })
    context = {
        "ticket_ids": join_ticket_ids([t["id"] for t in cr.get("tickets", [])]),
        "deploy_date": cr.get("deploy_date", ""),
        "repos": repos_ctx,
    }
    tpl.render(context, autoescape=True)
    tpl.save(out_path)
