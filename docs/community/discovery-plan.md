# ResultSeal discovery plan

Reviewed 2026-11-09 against GitHub, Google Search Central and community guidance.
This is a rollout plan, not evidence that rankings or adoption have improved.

## Starting point

GitHub reported 5 stars and 8 forks, no open issues, and v0.2.0 as the latest
release. The default branch was `711977f`, published on 2026-10-15. CI was green.
Pages was built from `master:/docs`; the live page had no meta description.
The repository already had 20 topics, a PyPI listing and seven framework examples.

The first job is to make the use case easy to recognize and try. More topics,
repeated keywords or frequent version bumps do not establish usefulness.

## Position and search intent

Describe ResultSeal as **Python validation contracts for AI-agent tool results**.
Use the same description on GitHub, PyPI, the README and the playground.

| Reader's problem | Existing proof to show | Destination |
|---|---|---|
| An empty result became a confident absence claim | `empty-result.yaml`, `explicit-not-found.yaml` | README quickstart |
| An MCP tool returned an error or partial object | MCP examples and schema-required checks | Adapter spec and playground |
| A cached response was too old | `stale-response.yaml` | Freshness contract docs |
| An agent reported an unverified mutation | `unverified-write.yaml` | Effect-evidence explanation |
| Add a guard to a framework tool | Seven small integration examples | Relevant example file |

These are editorial search intents inferred from the code, not measured keyword
volumes. Use phrases such as “validate MCP tool results” and “empty agent tool
response” where they describe the example. Keep framework names beside working
examples rather than repeating them in every paragraph.

## Repository and Pages changes

- Lead the README with the language, problem and supported input shapes. Keep
  the runnable Python quickstart and CLI examples. Explain schema-validation
  limits and what a seal proves.
- Use an accurate About description and relevant topics. Remove `mcp-server`:
  ResultSeal consumes MCP-style results but does not run an MCP server. Add
  framework topics only when the repository includes that framework's example.
- Add a Pages description, canonical URL, Open Graph and large-card metadata.
  The 1280×640 preview uses the existing logo and accurate dependency information;
  its source is `assets/social-preview.svg`, exported as `docs/social-preview.png`.
  The SVG references `assets/logo.png`; keep that file available when exporting
  an updated PNG from the SVG.
  Changing the website metadata does not change GitHub's uploaded repository
  preview. Set that separately under repository Settings → Social preview → Edit
  using the same PNG. [GitHub's preview guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)
  recommends 1280×640 for best display and a file smaller than 1 MB.
- Put a plain explanation and quickstart link in static HTML so the page is
  useful before the playground JavaScript runs.
- Keep packaging links absolute so the same README works on PyPI.

GitHub supports topic search and recommends topics that describe purpose,
community and language, with a maximum of 20. Its documentation does not promise
rankings from a topic recipe. Google recommends accurate titles, useful text,
descriptions and links; its guidance offers no first-place guarantee.

Sources: [GitHub topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics),
[GitHub READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes),
[Google SEO starter guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide).

## First month after the fixes are published

| When | Action | Evidence to keep |
|---|---|---|
| Day 0 | Run the checks and publish reviewed fixes. Smoke-test the deployed playground and clean PyPI installation after release. | Commit, CI run, release and deployed-page URLs |
| Days 1–3 | Record a 30–45 second demo of empty, complete and missing-field observations. Share it on one account you maintain, using the drafts as a starting point. | Post URL, questions, link clicks if available |
| Days 4–7 | Share one framework-specific example in a community that permits it. Be available to explain the implementation. | Thread URL and concrete response shapes reported |
| Week 2 | Turn one real, sanitized failure report into a fixture or improve the example people struggled with. | Issue, fixture and regression test |
| Week 3 | Check one relevant library/tools directory's rules and propose one accurate entry if it fits. | Maintainer feedback; accepted entry if any |
| Week 4 | Compare traffic, clones and independent usage with the baseline. Fix the most common adoption obstacle. | Weekly notes and next decision |

HN requires human-written posts and comments, a project people can try and no
solicited votes. Prepare the technical facts; the maintainer writes and submits
any HN post. A routine release is not a reason to repost.
[Show HN rules](https://news.ycombinator.com/showhn.html),
[HN guidelines](https://news.ycombinator.com/newsguidelines.html).

Do not submit to `awesome-mcp-servers`: its stated scope is installable servers.
The [Awesome LangChain tools list](https://github.com/kyrolabs/awesome-langchain#tools)
is a candidate because ResultSeal ships a LangChain guard. Its
[contribution guide](https://github.com/kyrolabs/awesome-langchain/blob/master/contributing.md)
requires maintenance, traction and clear value. Gather usage evidence before
proposing an entry, then append it at the bottom of the appropriate list.
Placement is a maintainer decision.

## Measurement

Record baseline and weekly snapshots privately in the maintainer's playbook:

```bash
gh repo view sx4im/resultseal --json stargazerCount,forkCount,repositoryTopics
gh api repos/sx4im/resultseal/traffic/views
gh api repos/sx4im/resultseal/traffic/clones
gh api repos/sx4im/resultseal/traffic/popular/referrers
```

GitHub traffic requires push access and covers the past 14 days, so save
snapshots weekly. [GitHub's traffic documentation](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository)
describes the window and update intervals. Track views and unique visitors, clones, referring sites,
issues containing a real failure case, and independent integration attempts.
Stars are useful context but do not demonstrate use. Treat an increase after a
post as correlation unless referrer data or user feedback connects them.

First-month experiment targets: one independent integration attempt, three
specific usability reports and one new fixture from an external response shape.
These are targets, not forecasts. If traffic rises but nobody can run the
quickstart, prioritize adoption fixes before another announcement.
