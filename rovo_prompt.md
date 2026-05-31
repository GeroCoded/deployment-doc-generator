# Rovo prompt — generate `deployment.yml`

Paste this into Rovo, then list the ticket IDs going into the deployment. Rovo
fills the **facts**; it must leave **human-judgment** fields as `TODO:` so you
notice and complete them.

---

You are preparing a deployment manifest. I will give you a list of Jira ticket IDs
that ship together in one Change Request.

For EACH ticket, read the ticket (description, comments, and any linked Confluence
pages or attachments) and produce concise, professional answers to:
- problem: What is the problem this ticket solves?
- user_impact: How does/did this affect the users?
- solution: What solution was implemented?
- testing: How was it tested?

Also collect the list of repositories each ticket touches from the ticket's repo
labels, and union them across all tickets.

Output **only** a valid YAML document, no prose, in exactly this shape:

```yaml
change_request:
  cr_number: "TODO: change request number"
  deploy_date: "TODO: YYYY-MM-DD"
  github_base: "https://github.domain.com"
  org: "my-org"

  tickets:
    - id: "<TICKET-ID>"
      title: "<ticket title>"
      problem: "<from ticket>"
      user_impact: "<from ticket>"
      solution: "<from ticket>"
      testing: "<from ticket>"

  repos:
    - name: "<repo from labels>"
      prod_tag: "TODO: current PROD tag"
      deploy_tag: "TODO: tag to deploy"

  business_justification: "TODO"
  change_summary: "TODO"
  impact_if_not_deployed: "TODO"
  worst_case: "TODO"
  rollback_plan: "TODO"
  deployment_steps:
    - "TODO"
```

Rules:
- Fill `tickets[*]` and the `repos[*].name` list from the tickets. Leave every
  `tag`, date, CR number, and the bottom risk/justification/steps block as `TODO`,
  because those are human decisions.
- Never invent tag names, dates, or rollback steps.
- Keep each answer to 1–3 sentences.
