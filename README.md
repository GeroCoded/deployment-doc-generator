# deploydoc — deployment documentation generator

Generates the three deployment documents from **one** source-of-truth manifest:

| Document | File | What it contains |
|---|---|---|
| Technical Summary | `Technical Summary.docx` | Index + one section per ticket with the 4 standard questions |
| Code Comparison | `Code Comparison.docx` | One section per repo: deploy/PROD tag links, compare link, commit list, `--stat`, and the **colored `git diff`** (replaces screenshots) |
| Change Request | `Change Request.xlsx` | The company template, column B filled from the manifest |

You assemble the facts about a deployment **once** (mostly via Rovo); the tool
emits all three documents. It runs **inside the VDI** where the repos live —
nothing leaves the machine.

## How it fits together

```
Rovo  ──► deployment.yml ──►  deploydoc  ──►  3 documents
(facts)   (+ you fill        (reads local
           the TODO            git for diffs)
           human fields)
```

- **Deterministic / auto:** ticket IDs & titles, repos, commit list, `git diff`,
  `--stat`, all GitHub tag/compare links, the index — never typed by hand.
- **AI-drafted (Rovo), you approve:** the 4 ticket answers + Excel justification/summary.
- **Human-only:** tags to deploy, deployment steps, rollback — left as `TODO:`
  in the manifest and flagged on every run.

## Install

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt      # docxtpl, openpyxl, jinja2, pyyaml
```

> If the VDI can't reach public PyPI, point pip at the internal mirror:
> `pip install -r requirements.txt -i https://<nexus-host>/repository/pypi/simple`

## Use

1. **Generate the manifest** — paste `rovo_prompt.md` into Rovo with your ticket IDs.
   Save the YAML as `deployment.yml`. Fill in the `TODO:` fields (tags, steps, risks).
2. **Run:**
   ```bash
   python -m deploydoc generate --manifest deployment.yml --out ./out
   ```
   Output lands in `./out/`. Any unfilled `TODO:` is listed; a missing git tag
   aborts that repo loudly (it will never emit an empty diff). `--strict` makes
   any repo error fail the whole run.

## Adapting your company templates (one-time)

The tool fills **your branded templates**; it does not impose a layout. Run
`python templates/make_reference_templates.py` to produce reference copies that
show the exact markup, then mirror these placeholders into your real files:

**Technical Summary (.docx)** — uses [docxtpl](https://docxtpl.readthedocs.io) Jinja tags:
- Title: `Technical Summary - {{ ticket_ids }}`
- Repeat per ticket — wrap the ticket section between paragraphs containing
  `{%p for t in tickets %}` and `{%p endfor %}`. Inside: heading `{{ t.id }}: {{ t.title }}`
  and fields `{{ t.problem }}`, `{{ t.user_impact }}`, `{{ t.solution }}`, `{{ t.testing }}`.
- Keep your existing Word **Table of Contents** field for the index — it covers Heading 1.

**Code Comparison (.docx):**
- Wrap the repo section between `{%p for repo in repos %}` and `{%p endfor %}`.
- Heading `{{ repo.name }}`; bullets use **RichText** (note the `r`):
  `Version to be deployed: {{r repo.deploy_link }}`,
  `Current PROD version: {{r repo.prod_link }}`,
  `Comparison Link: {{r repo.compare_link }}`.
- `{{ repo.stat }}`, the commit list `{{r repo.commits_rich }}`, and the colored
  diff `{{r repo.diff_rich }}`.

**Change Request (.xlsx):**
- Put placeholders in **column B** next to each question. Available fields:
  `{{ cr_number }}`, `{{ deploy_date }}`, `{{ ticket_ids }}`, `{{ repo_names }}`,
  `{{ deploy_versions }}`, `{{ backout_versions }}`, `{{ business_justification }}`,
  `{{ change_summary }}`, `{{ impact_if_not_deployed }}`, `{{ worst_case }}`,
  `{{ rollback_plan }}`, `{{ deployment_steps | lines }}`.
- Column A and all formatting are untouched.

> ⚠️ docx requires `autoescape=True` (already set) — without it, any `&`, `<`, or
> `>` in your text is silently dropped and the colored diff disappears entirely.

## Configuration

Per-deployment values live in the manifest (`github_base`, `org`, `exclude`,
`max_diff_lines`). A few can also go in an optional `deploydoc.prefs.yml`:

```yaml
repos_root: "/home/me/work/repos"   # find repos by name without a per-repo path (Q-B)
github_base: "https://github.domain.com"
org: "my-org"
exclude: ["package-lock.json", "*.snap"]
max_diff_lines: 4000
```

## Security notes (for review)

- Runs fully locally: reads your git clones, writes 3 files. No source is uploaded.
- Network: only an optional `git fetch --tags` (disable with `--no-fetch`). Skip it
  entirely and the tool works offline.
- The only external calls in the whole pipeline are Rovo (already approved) building
  the manifest text.

## Roadmap

- **Phase 2:** direct Jira API to pre-fill the manifest (skip the Rovo copy step) —
  once API access is confirmed.
- **Phase 3:** wrap in a CLI / package it for the central AI-tools repo.
