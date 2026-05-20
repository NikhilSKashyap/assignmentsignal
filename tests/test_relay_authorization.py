from assignment.core.setup import student_package
from assignment.core.session import _github_authenticated_push_url
from assignment.relay.store import SessionStore, make_github_cid


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
        "allow_multiple_submissions": True,
    }

    public = student_package(payload)

    assert public["submit_token"] == "student-submit-token"
    assert public["allow_multiple_submissions"] is True
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


def test_github_cid_allows_multiple_attempts_for_same_account():
    first = make_github_cid(12345, "state-one")
    second = make_github_cid(12345, "state-two")

    assert first != second
    assert make_github_cid(12345, "state-one") == first


def test_github_submission_history_keeps_multiple_attempts(tmp_path):
    store = SessionStore(tmp_path)

    store.record_github_submission("ASG-1234-AB", 12345, "cid-one")
    store.record_github_submission("ASG-1234-AB", 12345, "cid-two")

    history = store._load_json(store._github_subs_path())
    assert history["ASG-1234-AB"]["12345"] == ["cid-one", "cid-two"]


def test_assignment_multiple_submission_policy_defaults_off(tmp_path):
    store = SessionStore(tmp_path)
    hm_key = store.register_hm()
    code = "ASG-1234-AB"

    store.register_assignment(hm_key, code, {"code": code, "problem": "Build", "rubric": "Grade"})

    assert store.allow_multiple_submissions(hm_key, code) is False


def test_assignment_multiple_submission_policy_can_be_enabled(tmp_path):
    store = SessionStore(tmp_path)
    hm_key = store.register_hm()
    code = "ASG-1234-AB"

    store.register_assignment(
        hm_key,
        code,
        {
            "code": code,
            "problem": "Build",
            "rubric": "Grade",
            "allow_multiple_submissions": True,
        },
    )

    assert store.allow_multiple_submissions(hm_key, code) is True


def test_email_duplicate_detection_uses_saved_session_meta(tmp_path):
    store = SessionStore(tmp_path)
    hm_key = store.register_hm()
    code = "ASG-1234-AB"
    cid = "student-cid"

    store.save_session(
        hm_key,
        code,
        cid,
        "student@example.edu",
        {
            "manifest.json": b'{"elapsed_minutes": 1}',
            "events.jsonl": b'{"type":"session_start"}\n',
        },
    )

    assert store.check_email_duplicate(hm_key, code, "STUDENT@example.edu") is True
    assert store.check_email_duplicate(hm_key, code, "other@example.edu") is False
