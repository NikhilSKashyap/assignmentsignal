---
name: assignment-submit
description: "Submit an active AssignmentSignal session. Seals the log, generates the report, sends it to the professor/TA relay, and shows student-safe confirmation only."
trigger: /submit
---

# AssignmentSignal `/submit`

Use this workflow only when an AssignmentSignal session is active.

## Step 1: Check Status

```bash
python -m assignment.core.session status
```

If no active assignment session exists, say:

```text
No active assignment session. Start one with `/assignment <CODE>`.
```

## Step 2: Seal

```bash
python -m assignment.core.session seal
```

Extract the assignment code and elapsed time from the output or active session state.

## Step 3: Generate and Send

```bash
python -m assignment.core.report generate --code <CODE>
python -m assignment.core.transport send --code <CODE>
```

## Step 4: Student-Safe Confirmation

Show only:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Submitted — <CODE>
  Status: received by professor/TA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If a GitHub repo URL is present in the sealed manifest, include:

```text
  Code repository: <github_repo_url>
```

Never show scores, rubric assessment, ranking, grading notes, or AI evaluation to the student.

