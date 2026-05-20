from pathlib import Path
from tempfile import TemporaryDirectory

from assignment.cli import _upsert_assignment_agents_entry


ROOT = Path(__file__).resolve().parents[1]


def test_assignment_skill_relays_start_output():
    skill = ROOT / "assignment" / "skills" / "assignment" / "SKILL.md"
    text = skill.read_text()

    assert "show the full assignment banner and problem statement from stdout" in text
    assert "active_session.json" in text
    assert "output nothing else" not in text


def test_codex_installer_relays_start_output():
    cli = ROOT / "assignment" / "cli.py"
    text = cli.read_text()

    assert "show the full assignment banner and problem statement" in text
    assert "Codex global AGENTS.md updated" in text
    assert "active_session.json" in text
    assert "After the command prints the assignment banner and problem, output nothing else" not in text


def test_codex_installer_replaces_stale_assignment_block():
    stale = """# AssignmentSignal

When the user types `/assignment <CODE>`, this is an AssignmentSignal student session.

After the command prints the assignment banner and problem statement, output nothing else.
"""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "AGENTS.md"
        path.write_text(stale)

        _upsert_assignment_agents_entry(path)

        text = path.read_text()
        assert "show the full assignment banner and problem statement" in text
        assert "active_session.json" in text
        assert "output nothing else" not in text


def test_codex_installer_preserves_unrelated_agents_sections():
    existing = """# graphify
Keep this section.

## assignment skill
After the command prints the assignment banner and problem statement, output nothing else.

## other skill
Keep this too.
"""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "AGENTS.md"
        path.write_text(existing)

        _upsert_assignment_agents_entry(path)

        text = path.read_text()
        assert "# graphify" in text
        assert "## other skill" in text
        assert "show the full assignment banner and problem statement" in text
        assert "output nothing else" not in text
