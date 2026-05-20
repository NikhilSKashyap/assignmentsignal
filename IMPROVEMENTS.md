# AssignmentSignal Improvements

AssignmentSignal should become easy enough for a professor or TA to use without terminal comfort, while still being deployable and governable by a university IT team.

## Professor and TA Experience

- Ship native desktop apps for macOS (`.dmg`) and Windows (`.exe`) that wrap the dashboard, setup wizard, updates, and local diagnostics.
- Make first-run setup a guided checklist: create course, add assignment, invite TAs, connect relay, connect GitHub, test a sample student submission.
- Replace shared reviewer secrets with proper professor, TA, and course roles.
- Add TA queues, ownership, review status, and comment-only access modes.
- Add roster import from CSV as the baseline, then LMS import later.
- Add assignment templates for common CS coursework: scripts, notebooks, web apps, data analysis, and autograded projects.
- Add rubric authoring with evidence-linked grading, so every score can point to session moments, code diffs, or test output.
- Add instructor-facing explainability: what the student tried first, where they got stuck, what AI did, what the student appeared to understand, and what may need follow-up.
- Add one-click export to gradebook-friendly CSV with configurable fields.

## Student Experience

- Make install and start as close to one click as possible, with copy-paste fallback for technical students.
- Provide a student preflight check: identity, GitHub auth, assignment code, repo access, network, and assistant hook capture.
- Make `/assignment <CODE>` failures self-explanatory and recoverable.
- Add a small local status UI so students can see that recording is active, what will be submitted, and that scores remain instructor-only.
- Keep submission confirmation simple: submitted, timestamp, private repo link if available, and next steps from the professor.
- Add guardrails that clearly distinguish allowed AI collaboration from prohibited shortcuts based on the professor's policy.

## IT and Relay Setup

- Provide a Render-first relay setup path for small teams and a Docker Compose path for IT.
- Add a relay health dashboard with storage, OAuth, OpenAI grading, GitHub repo creation, and email delivery checks.
- Add backup and restore commands for `/data`.
- Add database/object storage backends for schools that outgrow single-disk Render deployments.
- Add institution-level OAuth, SSO, audit logs, retention policies, and per-course data boundaries.
- Publish a deployment guide for small college instructors, department admins, and central IT.

## Packaging

- Keep `pip install assignmentsignal` for technical users and automation.
- Add signed macOS and Windows desktop installers for professors and TAs.
- Add an auto-update mechanism for the desktop app.
- Keep the relay separate from the professor app so colleges can choose hosted, department-managed, or local-only workflows.

## Engineering Cleanup

- Rename internal `candidate` and `hm_key` concepts to `student` and `reviewer_key` or role-based equivalents in a compatibility-breaking migration.
- Remove InterviewSignal-era language from code comments, tests, prompts, and internal APIs.
- Add mocked GitHub tests for private repo creation, collaborator invites, and OAuth scopes.
- Add browser-level tests for dashboard setup, assignment creation, grading, and submission review.
- Move decision-state remnants behind a future feature flag if professor workflow needs structured outcomes later.
