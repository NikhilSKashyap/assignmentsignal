from pathlib import Path


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
