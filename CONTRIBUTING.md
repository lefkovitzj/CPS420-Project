# Contributing (draft)

Proposed conventions for this project's pull requests, issues, and branches.

## PR and issue titles

Use `<type>: <short description>`. Add an optional scope as
`<type>(<scope>): <short description>` when it helps identify the affected area.
Use an action verb, sentence case, and no trailing period.

| Type | Use for |
| --- | --- |
| `feat` | New functionality or improvements |
| `fix` | Bug fixes |
| `docs` | Documentation |
| `refactor` | Code restructuring without behavior changes |
| `test` | Adding or updating tests |
| `ci` | Continuous integration workflows |
| `chore` | Setup, dependencies, and other maintenance |

Examples:

- `feat(matching): Match users by shared courses`
- `fix(chat): Prevent duplicate messages`
- `docs: Document local setup`

An issue title describes the intended work; a PR title describes the change it
delivers. They can match when a PR completes a single issue. Link issues in the
PR body using `Closes #123` when the PR completes them, or `Related to #123`
when work remains.

## Branch names

Use `<type>/<issue-number>-<short-description>` with the types above. Use
lowercase words separated by hyphens; omit `#` from the issue number.
If there is no issue, use `<type>/<short-description>`.

- `feat/42-match-by-shared-courses`
- `fix/57-prevent-duplicate-messages`
- `docs/document-local-setup`

## Templates

- [Pull request](.github/pull_request_template.md)
- [Bug report](.github/ISSUE_TEMPLATE/bug_report.md)
- [Feature request](.github/ISSUE_TEMPLATE/feature_request.md)
- [General task](.github/ISSUE_TEMPLATE/task.md)

GitHub uses these templates when creating PRs and issues after the files are
merged into the repository's default branch. Replace prompts with relevant
details and remove optional sections that do not apply.
