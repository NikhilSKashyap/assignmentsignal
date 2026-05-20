from assignment.core.setup import student_package
from assignment.core.session import _github_authenticated_push_url
from assignment.relay.store import SessionStore


def test_student_package_never_exposes_hm_key():
    payload = {
        "code": "ASG-1234-AB",
        "problem": "Build something",
        "rubric": "Private scoring notes",
        "hm_key": "admin-secret",
        "relay_url": "https://relay.example",
        "submit_token": "student-submit-token",
        "created_at": 1,
        "problem_hash": "abc123",
    }

    public = student_package(payload)

    assert public["submit_token"] == "student-submit-token"
    assert "hm_key" not in public
    assert "rubric" not in public


def test_relay_candidate_payload_uses_scoped_submit_token(tmp_path):
    store = SessionStore(tmp_path)
    hm_key = store.register_hm()
    code = "ASG-1234-AB"

    store.register_assignment(
        hm_key,
        code,
        {
            "code": code,
            "problem": "Build something",
            "rubric": "Private scoring notes",
            "hm_key": hm_key,
            "relay_url": "https://relay.example",
        },
    )

    public = store.get_assignment_candidate(hm_key, code)

    assert public is not None
    assert public["code"] == code
    assert public["submit_token"]
    assert "hm_key" not in public
    assert "rubric" not in public
    assert store.verify_submit_token(hm_key, code, public["submit_token"])
    assert not store.verify_submit_token(hm_key, code, "wrong-token")


def test_github_push_url_uses_token_username_and_git_suffix():
    url = _github_authenticated_push_url("https://github.com/student/assignment-ASG-1", "tok:en")

    assert url == "https://x-access-token:tok%3Aen@github.com/student/assignment-ASG-1.git"
