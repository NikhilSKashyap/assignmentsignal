---
name: assignment
description: "AssignmentSignal student session. Type `/assignment <CODE>` to start an assignment session that captures prompts, tool calls, file changes, and submission evidence for professor/TA review."
trigger: /assignment
---

# AssignmentSignal `/assignment`

When the user types `/assignment <CODE>`, immediately run:

```bash
python -m assignment.core.session start --code <CODE>
```

Do not browse the repo first. Do not explain the command first. Do not ask for confirmation.

After the command completes, show the full assignment banner and problem statement from stdout to the student verbatim. Do not add commentary before or after it. Wait for the student's next message and treat all subsequent work as part of the active assignment session.

## While Active

The assignment session captures tool use and file changes. Continue normal coding help inside the student's workspace.

If the student asks for status, run:

```bash
python -m assignment.core.session status
```

## Submit

When the user types `/submit` during an active AssignmentSignal session, run:

```bash
python -m assignment.core.session seal
python -m assignment.core.report generate --code <CODE>
python -m assignment.core.transport send --code <CODE>
```

Show only the submission confirmation. Never show scores, rubric notes, grading summaries, ranking, or AI evaluation to students.
