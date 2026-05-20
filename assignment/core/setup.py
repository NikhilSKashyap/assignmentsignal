"""
assignment.core.setup
--------------------
Handles professor/TA assignment creation: encodes the assignment package into a
signed token, stores it (locally or via relay), and returns the assignment code.
"""

import argparse
import base64
import hashlib
import json
import os
import random
import secrets
import string
import time
from pathlib import Path

ASSIGNMENT_DIR = Path.home() / ".assignment"
SESSIONS_DIR = ASSIGNMENT_DIR / "sessions"
CREATED_DIR = ASSIGNMENT_DIR / "created"


def ensure_dirs():
    for d in [ASSIGNMENT_DIR, SESSIONS_DIR, CREATED_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def generate_code() -> str:
    """Generate a human-readable assignment code like ASG-4829-XK."""
    digits = "".join(random.choices(string.digits, k=4))
    letters = "".join(random.choices(string.ascii_uppercase, k=2))
    return f"ASG-{digits}-{letters}"


def encode_package(payload: dict) -> str:
    """Base64-encode the assignment payload for embedding in the code token."""
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def student_package(payload: dict) -> dict:
    """Return only fields safe for a student to receive."""
    allowed = {
        "code",
        "problem",
        "time_limit_minutes",
        "relay_url",
        "submit_token",
        "created_at",
        "problem_hash",
        "reviewer_github_usernames",
    }
    return {k: v for k, v in payload.items() if k in allowed}


# Backward-compatible name used by older tests/docs during the v0 fork.
candidate_package = student_package


def create_assignment(
    problem: str,
    rubric: str,
    professor_email: str = "",
    cc_emails: list[str] | None = None,
    student_email: str | None = None,
    reviewer_github_usernames: list[str] | None = None,
    time_limit_minutes: int | None = None,
    audit_email: str | None = None,
) -> dict:
    cc_emails = cc_emails or []
    reviewer_github_usernames = reviewer_github_usernames or []
    ensure_dirs()

    code = generate_code()
    created_at = int(time.time())

    # Embed the instructor relay config so students need zero transport setup.
    relay_url = ""
    hm_key = ""
    try:
        from assignment.core.transport import get_relay_url, get_hm_key
        relay_url = get_relay_url() or ""
        hm_key = get_hm_key() if relay_url else ""
    except Exception:
        pass

    # Students do not see scores in AssignmentSignal. Professors/TAs review
    # grades privately in the dashboard.
    sharing_config = {"score": "none"}

    payload = {
        "code": code,
        "problem": problem,
        "rubric": rubric,
        "hm_email": professor_email,
        "professor_email": professor_email,
        "cc_emails": cc_emails,
        "candidate_email": student_email,
        "student_email": student_email,
        "reviewer_github_usernames": reviewer_github_usernames,
        "time_limit_minutes": time_limit_minutes,
        "anonymize": False,
        "audit_email": audit_email,
        "created_at": created_at,
        "sharing": sharing_config,
        # Integrity: hash of the problem + rubric so students can't claim
        # the problem was different
        "problem_hash": hashlib.sha256(problem.encode()).hexdigest()[:16],
        # Transport: relay config flows instructor → package → student.
        # hm_key stays instructor-only; submit_token is scoped to student submission.
        "relay_url": relay_url,
        "hm_key": hm_key,
        "submit_token": secrets.token_urlsafe(32),
        "auto_grade": True,
    }

    # Save locally on the professor/TA machine
    assignment_file = CREATED_DIR / f"{code}.json"
    assignment_file.write_text(json.dumps(payload, indent=2))

    # Also write an encoded token (for offline/embedded sharing)
    token = encode_package(student_package(payload))
    token_file = CREATED_DIR / f"{code}.token"
    token_file.write_text(token)

    # Push to relay so students can fetch via code (no file transfer needed).
    if relay_url and hm_key:
        try:
            from assignment.core.transport import RelayTransport
            rt = RelayTransport(relay_url, hm_key=hm_key)
            rt.push_assignment(code, payload)
        except Exception as e:
            print(f"  ⚠ Could not push assignment to relay: {e}")
            print(f"    Students will need the token string to start instead.")

    return {"code": code, "payload": payload, "token": token}


def load_assignment(code: str) -> dict | None:
    """
    Load an assignment package by code.
    Checks local storage first (for student who received the full token),
    then falls back to relay lookup.
    """
    # 1. Check local created/ (professor/TA running on same machine — dev/testing)
    local_file = CREATED_DIR / f"{code}.json"
    if local_file.exists():
        return json.loads(local_file.read_text())

    # 2. Check if it's an embedded token (code is actually a token string)
    try:
        decoded = base64.urlsafe_b64decode(code.encode() + b"==")
        payload = json.loads(decoded)
        if "code" in payload and "problem" in payload:
            return payload
    except Exception:
        pass

    # 3. Relay lookup — fetch the package from the relay (no auth needed)
    try:
        from assignment.core.transport import get_relay_url, RelayTransport, TransportError
        relay_url = get_relay_url()
        if relay_url:
            rt = RelayTransport(relay_url)
            return rt.get_assignment(code)
    except Exception:
        pass

    return None


def main():
    parser = argparse.ArgumentParser(description="Create an assignment session")
    parser.add_argument("command", choices=["create"])
    parser.add_argument("--problem-file", default=None)
    parser.add_argument("--rubric-file", default=None)
    parser.add_argument("--problem", default=None, help="Problem text directly (alternative to --problem-file)")
    parser.add_argument("--rubric", default=None, help="Rubric text directly (alternative to --rubric-file)")
    parser.add_argument("--professor-email", "--hm-email", dest="professor_email", default="")
    parser.add_argument("--cc-emails", default="")
    parser.add_argument("--student-email", "--candidate-email", dest="student_email", default=None)
    parser.add_argument("--reviewer-github-usernames", default="")
    parser.add_argument("--time-limit", type=int, default=None)
    parser.add_argument("--audit-email", default=None)
    args = parser.parse_args()

    if args.problem:
        problem = args.problem.strip()
    elif args.problem_file:
        problem = Path(args.problem_file).read_text().strip()
    else:
        raise SystemExit("error: --problem or --problem-file is required")

    if args.rubric:
        rubric = args.rubric.strip()
    elif args.rubric_file:
        rubric = Path(args.rubric_file).read_text().strip()
    else:
        raise SystemExit("error: --rubric or --rubric-file is required")
    cc_emails = [e.strip() for e in args.cc_emails.split(",") if e.strip()]
    reviewer_github_usernames = [
        u.strip().lstrip("@") for u in args.reviewer_github_usernames.split(",") if u.strip()
    ]

    result = create_assignment(
        problem=problem,
        rubric=rubric,
        professor_email=args.professor_email,
        cc_emails=cc_emails,
        student_email=args.student_email,
        reviewer_github_usernames=reviewer_github_usernames,
        time_limit_minutes=args.time_limit,
        audit_email=args.audit_email,
    )

    relay_url = result["payload"].get("relay_url", "")
    print(f"\n✓ Assignment created.\n")
    print(f"  Code: {result['code']}\n")
    print(f"Share this code with your students. They run:\n")
    print(f"  pip install assignmentsignal && assignment install")
    print(f"  /assignment {result['code']}\n")
    if relay_url:
        print(f"Students appear in your dashboard when they submit.")
        print(f"  assignment dashboard\n")
    else:
        print(f"You'll receive the full session report by email when they submit.")
        print(f"To review students: assignment dashboard\n")


if __name__ == "__main__":
    main()
