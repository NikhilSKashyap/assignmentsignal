# assignmentsignal

AssignmentSignal helps professors and TAs see how students worked through an assignment, not just the final files they submitted.

It is the academic sibling of InterviewSignal: one assignment code, many students, private GitHub repos, captured AI-assistant workflow, and a professor/TA dashboard for review.

## v0 Scope

- Professors or TAs create assignments from the dashboard.
- Students start a session with `/assignment <CODE>`.
- The session captures prompts, tool calls, file changes, diffs, commits, and a tamper-evident event log.
- If GitHub OAuth is configured on the relay, AssignmentSignal creates a private repo named `assignment-<CODE>` for the student session.
- Professor/TA GitHub usernames entered during assignment setup are invited to the private repo.
- On `/submit`, the student sees submission confirmation only. Scores are instructor-only.
- Professors and TAs see the same dashboard from their own machines when connected to the same relay credentials.

## Install

```bash
pip install assignmentsignal
assignment install
```

## Professor / TA Flow

```bash
assignment dashboard
```

The dashboard handles setup, assignment creation, grading, review, comments, decisions, and exports.

For v0, the relay credentials are intentionally blank in local config and Docker defaults. A separate AssignmentSignal relay should be created later and configured with:

```bash
assignment configure-relay
assignment configure-api-key
```

Optional relay environment variables:

```bash
RELAY_API_KEY=
GRADING_API_KEY=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
RELAY_BASE_URL=
```

## Student Flow

```bash
assignment install
/assignment ASG-1234-AB
```

Students work normally in their assignment workspace. When done:

```bash
/submit
```

The student receives a confirmation. They do not see a score, rubric assessment, ranking, or grading summary.

## Relay

Run a local relay for development:

```bash
docker compose up --build
```

Or directly:

```bash
python -m assignment.relay.server
```

The relay defaults to dev mode if `RELAY_API_KEY` is blank. Production deployments should set a relay key, GitHub OAuth credentials, and a persistent `/data` volume.

## Notes

See [IMPROVEMENTS.md](IMPROVEMENTS.md) for product and engineering follow-ups discovered during the v0 fork.
