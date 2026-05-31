"""Validates a deployment.yml before rendering.

Now that the manifest may be written by an LLM (Copilot + Atlassian MCP), this
catches structural mistakes early with a clear message instead of failing deep
inside docx/xlsx rendering.

Returns (errors, warnings):
  - errors block generation (missing/garbled structure).
  - warnings are advisory (e.g. fields still left as TODO).
"""
from __future__ import annotations

REQUIRED_TICKET_FIELDS = ["id", "title", "problem", "user_impact", "solution", "testing"]
REQUIRED_REPO_FIELDS = ["name", "prod_tag", "deploy_tag"]


def _is_todo(v) -> bool:
    return isinstance(v, str) and v.strip().upper().startswith("TODO")


def validate_manifest(manifest) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(manifest, dict) or "change_request" not in manifest:
        return (["manifest has no top-level 'change_request' key"], [])
    cr = manifest["change_request"]
    if not isinstance(cr, dict):
        return (["'change_request' must be a mapping"], [])

    # Links need either github_base+org, or a per-repo repo_url.
    has_base = bool(cr.get("github_base"))
    has_org = bool(cr.get("org"))

    tickets = cr.get("tickets")
    if not tickets:
        errors.append("'tickets' is empty — at least one ticket is required")
    elif not isinstance(tickets, list):
        errors.append("'tickets' must be a list")
    else:
        for i, t in enumerate(tickets):
            label = f"tickets[{i}]"
            if not isinstance(t, dict):
                errors.append(f"{label} must be a mapping")
                continue
            for f in REQUIRED_TICKET_FIELDS:
                if f not in t or t[f] in (None, ""):
                    errors.append(f"{label} is missing '{f}'")
                elif _is_todo(t[f]):
                    warnings.append(f"{label}.{f} is still TODO")

    repos = cr.get("repos")
    if not repos:
        errors.append("'repos' is empty — at least one repo is required")
    elif not isinstance(repos, list):
        errors.append("'repos' must be a list")
    else:
        for i, r in enumerate(repos):
            label = f"repos[{i}] ({r.get('name', '?') if isinstance(r, dict) else '?'})"
            if not isinstance(r, dict):
                errors.append(f"repos[{i}] must be a mapping")
                continue
            for f in REQUIRED_REPO_FIELDS:
                if f not in r or r[f] in (None, ""):
                    errors.append(f"{label} is missing '{f}'")
                elif _is_todo(r[f]):
                    warnings.append(f"{label}.{f} is still TODO")
            if not r.get("repo_url") and not (has_base and has_org):
                warnings.append(
                    f"{label}: no 'repo_url' and missing github_base/org — GitHub links may be wrong"
                )

    # Advisory: human-judgment fields left as TODO.
    for f in ["business_justification", "change_summary", "impact_if_not_deployed",
              "worst_case", "rollback_plan"]:
        if _is_todo(cr.get(f)):
            warnings.append(f"change_request.{f} is still TODO")
    steps = cr.get("deployment_steps") or []
    if any(_is_todo(s) for s in steps):
        warnings.append("change_request.deployment_steps still contains TODO")

    return errors, warnings
