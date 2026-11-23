# ResultSeal growth plan: contributors, plugin, launch

Reviewed 2026-11-23. Builds on [discovery-plan.md](discovery-plan.md); the
measurement section there still applies.

## Starting point

- 5 stars, 8 forks, 11 contributors, no open issues.
- Every past `good first issue` (15 of them) was closed, and 11 of the 15
  merged pull requests came from outside contributors. Well-scoped issues
  with file pointers and verification commands get picked up.
- The issue queue is empty, so new contributors currently have nothing to
  claim.

## What GitHub Trending needs

GitHub says Trending weighs stars, forks, commits, follows and pageviews,
with recent events counting most, and recomputes it several times a day for
daily, weekly and monthly windows
([GitHub blog](https://github.blog/news-insights/company-news/explore-what-is-trending-on-github/)).
Language pages are easier to reach than the all-languages page. Third-party
estimates put Python daily Trending at roughly 50–100 stars in a day; treat
that as a rough target, not a threshold.

Good first issues bring contributors, and contributors keep a project
active, but they do not produce that kind of one-day spike. A spike comes
from one concentrated launch of something people can try in a minute. The
plan below uses issues to build the contributor base and the Claude Code /
Codex plugin as the launch.

## Phase 1: refill the contributor queue

1. Open the ten drafted issues in [good-first-issues/](good-first-issues/):

   ```bash
   python scripts/open_good_first_issues.py           # dry run
   python scripts/open_good_first_issues.py --create  # open them
   ```

   They cover four CLI improvements, contract autocompletion, three
   real-backend fixtures (Stripe, Slack, kubectl), an OpenAI Agents SDK
   example and MCP `content` array support. Every expected outcome was
   checked against the current code. Delete the drafts once the issues are
   open.
2. Pin two or three of them. Reply to claims and pull requests within a day;
   response time is what turns a first contribution into a second one.
3. List the repository where beginners look for issues:
   - [goodfirstissue.dev](https://goodfirstissue.dev/) asks for at least 3
     open beginner-labeled issues, at least 10 contributors, a README,
     CONTRIBUTING.md, a license and recent activity. ResultSeal meets these
     once the issues are open. Submit through the form linked from
     [its README](https://github.com/DeepSourceCorp/good-first-issue).
   - [Up For Grabs](https://up-for-grabs.net/) takes a YAML file in a pull
     request, pointing at the `good first issue` label.
4. When fewer than three beginner issues remain open, draft the next batch.

## Phase 2: ship the Claude Code and Codex plugin

Coding agents call MCP tools all day, and both Claude Code and Codex run a
`PostToolUse` hook after each call. The plugin in `plugins/resultseal`
blocks empty, errored and incomplete MCP results there, which is
ResultSeal's existing check in the place where most people now meet the
problem.

1. Merge the plugin pull request and cut a release, so
   `claude plugin marketplace add sx4im/resultseal` and
   `codex plugin marketplace add sx4im/resultseal` work from the default
   branch.
2. Submit the plugin to Anthropic's directory from
   [claude.ai/directory/manage](https://claude.com/docs/plugins/submit). This
   needs a paid claude.ai plan; run
   `claude plugin validate --profile directory ./plugins/resultseal` first.
3. For Codex, keep the repository marketplace as the install path. OpenAI's
   documentation limits plugin-bundled hooks to manually installed plugins,
   so a public directory listing may not deliver the hook.
4. Propose entries on curated Claude Code and Codex plugin lists after
   reading each list's contribution rules.

## Phase 3: one launch window

Plan everything for the same 24–48 hours so stars and visits land in one
Trending window.

1. Record a 30–45 second demo: an agent calls an MCP tool that returns
   `[]` and claims "that customer doesn't exist"; with the plugin installed,
   the same call is blocked with `EMPTY_WITHOUT_NOT_FOUND_SENTINEL`.
2. Put the demo and the two install commands at the top of the README.
3. Post once each, written by the maintainer: Show HN (follow the
   [Show HN rules](https://news.ycombinator.com/showhn.html)), the Claude
   and Codex communities that allow project posts, r/Python's showcase
   thread, and the maintainer's own X and LinkedIn accounts. Stay in the
   threads to answer questions.
4. Have a few good first issues open that day, so visitors who want to help
   have something to pick up.

Do not buy stars, trade stars or ask for upvotes. GitHub's acceptable use
policies prohibit inauthentic activity, and HN penalizes solicited votes.

## Phase 4: keep the activity going

- Release when contributions land, and thank contributors by name in the
  release notes.
- Turn every reported real-world failure into a fixture issue.
- Open the design questions below as Discussions to attract experienced
  contributors.

## Design questions found while drafting issues

These are not beginner issues; they need a maintainer decision.

- A paginated result with `"has_more": true` seals when its required fields
  are present, although it is only one page of the answer.
- `check()` bounds a JSON string `body` as a single string (16 KiB) before
  parsing, while the nested loader allows 128 KiB documents, so a 20 KiB
  JSON body is refused as `LIMIT_EXCEEDED`.
- A required field that is present but empty (`"items": []`) satisfies
  `required_fields`, so a GitHub search with `total_count: 0` seals under a
  contract that requires `items`.
