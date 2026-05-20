"""
assignment CLI
-------------
Entry point for the `assignment` command.

Usage:
  assignment install              Install skill + hooks for Claude Code
  assignment install --platform codex
  assignment uninstall
  assignment configure-email      Set up SMTP credentials
  assignment dashboard            Open professor/TA dashboard
  assignment status               Show active session status
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ASSIGNMENT_DIR = Path.home() / ".assignment"
SKILL_SRC = Path(__file__).parent / "skills" / "assignment" / "SKILL.md"
SUBMIT_SKILL_SRC = Path(__file__).parent / "skills" / "submit" / "SKILL.md"


# ─── Platform install targets ────────────────────────────────────────────────

PLATFORMS = {
    "claude": {
        "name": "Claude Code",
        "skill_dir": Path.home() / ".claude" / "skills" / "assignment",
        "claude_md": Path.home() / ".claude" / "CLAUDE.md",
        "settings_json": Path.home() / ".claude" / "settings.json",
    },
    "codex": {
        "name": "Codex",
        "agents_md": Path("AGENTS.md"),
        "hooks_json": Path(".codex") / "hooks.json",
    },
    "cursor": {
        "name": "Cursor",
        "cursorrules": Path(".cursorrules"),
    },
    "gemini": {
        "name": "Gemini CLI",
        "gemini_md": Path("GEMINI.md"),
        "settings_json": Path(".gemini") / "settings.json",
    },
    "aider": {
        "name": "Aider",
        "config_yml": Path(".aider.conf.yml"),
        "conventions_md": Path("CONVENTIONS.md"),
    },
}


def _install_claude(verbose=True):
    """Install skill + PreToolUse/PostToolUse hooks for Claude Code."""
    cfg = PLATFORMS["claude"]

    # 1. Copy SKILL.md files
    skill_dir = cfg["skill_dir"]
    skill_dir.mkdir(parents=True, exist_ok=True)
    dest = skill_dir / "SKILL.md"
    shutil.copy2(SKILL_SRC, dest)
    if verbose:
        print(f"  ✓ Skill installed: {dest}")

    submit_skill_dir = Path.home() / ".claude" / "skills" / "submit"
    submit_skill_dir.mkdir(parents=True, exist_ok=True)
    submit_dest = submit_skill_dir / "SKILL.md"
    shutil.copy2(SUBMIT_SKILL_SRC, submit_dest)
    if verbose:
        print(f"  ✓ Skill installed: {submit_dest}")

    # 2. Update CLAUDE.md
    claude_md = cfg["claude_md"]
    assignment_entry = """
## assignment skill
- **assignment** (`~/.claude/skills/assignment/SKILL.md`) — AI-native assignment platform.
  - `/assignment <CODE>` — Student session (captures all activity)
  - `/submit` — Submit session to professor/TA
When the user types `/assignment` or `/submit`, invoke the Skill tool with `skill: "assignment"` before doing anything else.
"""
    if claude_md.exists():
        content = claude_md.read_text()
        if "assignment skill" not in content:
            claude_md.write_text(content + assignment_entry)
            if verbose:
                print(f"  ✓ CLAUDE.md updated: {claude_md}")
    else:
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(assignment_entry)
        if verbose:
            print(f"  ✓ CLAUDE.md created: {claude_md}")

    # 3. Install hooks in settings.json
    settings_json = cfg["settings_json"]
    if settings_json.exists():
        try:
            settings = json.loads(settings_json.read_text())
        except Exception:
            settings = {}
    else:
        settings = {}

    hook_cmd = f"{sys.executable} -m assignment.hooks.claude_hook"

    hooks = settings.setdefault("hooks", {})

    hooks["PreToolUse"] = [{
        "matcher": "*",
        "hooks": [{
            "type": "command",
            "command": f"{hook_cmd} pre",
        }]
    }]

    hooks["PostToolUse"] = [{
        "matcher": "*",
        "hooks": [{
            "type": "command",
            "command": f"{hook_cmd} post",
        }]
    }]

    # Stop hook — reads conversation log, logs user_prompt + assistant_message
    hooks["Stop"] = [{
        "hooks": [{
            "type": "command",
            "command": f"{hook_cmd} stop",
        }]
    }]

    # 4. Add permissions so assignment commands run without yes/no prompts
    # Use absolute paths computed at install time (like sys.executable) so they
    # work regardless of how Claude Code resolves ~ vs full paths.
    assignment_home = str(Path.home() / ".assignment")
    permissions = settings.setdefault("permissions", {})
    allow = permissions.setdefault("allow", [])
    assignment_permissions = [
        "Bash(echo *)",
        f"Bash({sys.executable} -m assignment.core.setup *)",
        f"Bash({sys.executable} -m assignment.core.session *)",
        f"Bash({sys.executable} -m assignment.core.report *)",
        f"Bash({sys.executable} -m assignment.core.transport *)",
        "Bash(python -m assignment.core.setup *)",
        "Bash(python -m assignment.core.session *)",
        "Bash(python -m assignment.core.report *)",
        "Bash(python -m assignment.core.transport *)",
        "Bash(python3 -m assignment.core.setup *)",
        "Bash(python3 -m assignment.core.session *)",
        "Bash(python3 -m assignment.core.report *)",
        "Bash(python3 -m assignment.core.transport *)",
        "Bash(git init)",
        "Bash(git add *)",
        "Bash(git commit *)",
        "Bash(git push *)",
        "Bash(git remote *)",
        f"Read({assignment_home}/*)",
        f"Write({assignment_home}/*)",
    ]
    for p in assignment_permissions:
        if p not in allow:
            allow.append(p)
    permissions["allow"] = allow

    settings_json.parent.mkdir(parents=True, exist_ok=True)
    settings_json.write_text(json.dumps(settings, indent=2))
    if verbose:
        print(f"  ✓ Hooks + permissions installed: {settings_json}")

    # Verify the hook is actually reachable in this Python environment
    import subprocess as _sp
    try:
        test = _sp.run(
            [sys.executable, "-m", "assignment.hooks.claude_hook", "pre"],
            input='{"tool_name":"Bash","tool_input":{}}',
            capture_output=True, text=True, timeout=5,
        )
        if test.returncode != 0:
            raise RuntimeError(test.stderr.strip())
        if verbose:
            print(f"  ✓ Hook reachability check passed")
    except Exception as e:
        print(f"\n  ⚠  Hook reachability check FAILED: {e}")
        print(f"     The hook command is: {hook_cmd} pre")
        print(f"     If Claude Code uses a different Python, sessions won't be captured.")
        print(f"     Fix: reinstall assignmentsignal inside Claude Code's Python environment.")


def _install_codex(verbose=True):
    """Install skill for Codex via AGENTS.md + hooks.json."""
    agents_md = Path("AGENTS.md")
    entry = """
## assignment skill
When the user types `/assignment <CODE>`, immediately run:

```bash
python -m assignment.core.session start --code <CODE>
```

After the command prints the assignment banner and problem, output nothing else.
Wait for the student's next message and treat all subsequent work as part of
the active assignment session.

When the user types `/submit`, immediately run:

```bash
python -m assignment.core.session seal
python -m assignment.core.report generate --code <CODE>
python -m assignment.core.transport send --code <CODE>
```

Show only the submission confirmation. Never show scores to students.
"""
    if agents_md.exists():
        content = agents_md.read_text()
        if "assignment skill" not in content:
            agents_md.write_text(content + entry)
    else:
        agents_md.write_text(entry)
    if verbose:
        print(f"  ✓ AGENTS.md updated")

    hooks_dir = Path(".codex")
    hooks_dir.mkdir(exist_ok=True)
    hooks_file = hooks_dir / "hooks.json"
    hooks = {}
    if hooks_file.exists():
        try:
            hooks = json.loads(hooks_file.read_text())
        except Exception:
            pass

    hook_cmd = f"{sys.executable} -m assignment.hooks.claude_hook"
    hooks["PreToolUse"] = {"command": f"{hook_cmd} pre"}
    hooks_file.write_text(json.dumps(hooks, indent=2))
    if verbose:
        print(f"  ✓ Codex hooks installed: {hooks_file}")


def _install_cursor(verbose=True):
    """Install skill instructions for Cursor via .cursorrules."""
    cursorrules = PLATFORMS["cursor"]["cursorrules"]
    entry = """
# assignmentsignal — AI-native assignment platform
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# When the user types `/assignment <CODE>`, start an assignment session:
#   1. Run: python -m assignment.core.session start --code <CODE>
#   2. Read ~/.assignment/active/meta.json for the problem statement
#   3. Present the problem and begin the session
#   4. All student work happens in the current project directory
#
# When the user types `/submit`, end the session:
#   1. Run: python -m assignment.core.session seal
#   2. Run: python -m assignment.core.transport submit
#   3. Show submission confirmation only; scores are instructor-only
#
# IMPORTANT: Capture all tool use (file writes, edits, terminal commands)
# by noting them in the session. The assignment system tracks student
# thought process through their interaction with the AI assistant.
#
# Permissions needed:
#   - Read/Write ~/.assignment/*
#   - Run python -m assignment.core.* commands
#   - Run git commands (init, add, commit, push, remote)
"""
    if cursorrules.exists():
        content = cursorrules.read_text()
        if "assignmentsignal" not in content:
            cursorrules.write_text(content + entry)
            if verbose:
                print(f"  ✓ .cursorrules updated: {cursorrules}")
        else:
            if verbose:
                print(f"  ✓ .cursorrules already configured")
    else:
        cursorrules.write_text(entry)
        if verbose:
            print(f"  ✓ .cursorrules created: {cursorrules}")

    if verbose:
        print(f"\n  ⚠  Cursor does not support lifecycle hooks.")
        print(f"     Activity capture is limited — student prompts and tool calls")
        print(f"     won't be logged automatically. For full capture, use Claude Code.")


def _install_gemini(verbose=True):
    """Install skill + hooks for Gemini CLI via GEMINI.md + .gemini/settings.json."""
    # 1. GEMINI.md — project-level instructions
    gemini_md = PLATFORMS["gemini"]["gemini_md"]
    entry = """
## assignment skill
- **assignment** — AI-native assignment platform (assignmentsignal).
  - `/assignment <CODE>` — Start a student session (captures all activity)
  - `/submit` — Seal session and submit report to professor/TA

When the user types `/assignment`, run:
  `python -m assignment.core.session start --code <CODE>`
then read ~/.assignment/active/meta.json for the problem.

When the user types `/submit`, run:
  `python -m assignment.core.session seal`
  `python -m assignment.core.transport submit`
"""
    if gemini_md.exists():
        content = gemini_md.read_text()
        if "assignmentsignal" not in content and "assignment skill" not in content:
            gemini_md.write_text(content + entry)
            if verbose:
                print(f"  ✓ GEMINI.md updated: {gemini_md}")
        else:
            if verbose:
                print(f"  ✓ GEMINI.md already configured")
    else:
        gemini_md.write_text(entry)
        if verbose:
            print(f"  ✓ GEMINI.md created: {gemini_md}")

    # 2. .gemini/settings.json — hooks for activity capture
    settings_dir = Path(".gemini")
    settings_dir.mkdir(exist_ok=True)
    settings_json = PLATFORMS["gemini"]["settings_json"]

    settings = {}
    if settings_json.exists():
        try:
            settings = json.loads(settings_json.read_text())
        except Exception:
            pass

    hook_cmd = f"{sys.executable} -m assignment.hooks.claude_hook"
    hooks = settings.setdefault("hooks", {})
    hooks["preToolUse"] = {"command": f"{hook_cmd} pre"}
    hooks["postToolUse"] = {"command": f"{hook_cmd} post"}

    settings_json.write_text(json.dumps(settings, indent=2))
    if verbose:
        print(f"  ✓ Hooks installed: {settings_json}")


def _install_aider(verbose=True):
    """Install skill instructions for Aider via .aider.conf.yml + CONVENTIONS.md."""
    # 1. CONVENTIONS.md — Aider reads this via the `read:` directive
    conventions = PLATFORMS["aider"]["conventions_md"]
    entry = """
## assignmentsignal — AI-native assignment platform

When the user types `/assignment <CODE>`, start an assignment session:
  1. Run: python -m assignment.core.session start --code <CODE>
  2. Read ~/.assignment/active/meta.json for the problem statement
  3. Present the problem and begin the session

When the user types `/submit`, end the session:
  1. Run: python -m assignment.core.session seal
  2. Run: python -m assignment.core.transport submit
  3. Show submission confirmation only; scores are instructor-only

All student work happens in the current project directory. Track file
writes, edits, and terminal commands — the assignment system captures
thought process through AI assistant interaction.
"""
    if conventions.exists():
        content = conventions.read_text()
        if "assignmentsignal" not in content:
            conventions.write_text(content + entry)
            if verbose:
                print(f"  ✓ CONVENTIONS.md updated: {conventions}")
        else:
            if verbose:
                print(f"  ✓ CONVENTIONS.md already configured")
    else:
        conventions.write_text(entry)
        if verbose:
            print(f"  ✓ CONVENTIONS.md created: {conventions}")

    # 2. .aider.conf.yml — tell Aider to load CONVENTIONS.md
    config_yml = PLATFORMS["aider"]["config_yml"]
    config_lines = []
    has_read = False
    if config_yml.exists():
        content = config_yml.read_text()
        config_lines = content.splitlines()
        for line in config_lines:
            if line.strip().startswith("read:") or "CONVENTIONS.md" in line:
                has_read = True
                break

    if not has_read:
        config_lines.append("read: [CONVENTIONS.md]")
        config_yml.write_text("\n".join(config_lines) + "\n")
        if verbose:
            print(f"  ✓ .aider.conf.yml updated: {config_yml}")
    else:
        if verbose:
            print(f"  ✓ .aider.conf.yml already configured")

    if verbose:
        print(f"\n  ⚠  Aider does not support lifecycle hooks.")
        print(f"     Activity capture is limited — candidate prompts and tool calls")
        print(f"     won't be logged automatically. For full capture, use Claude Code.")


def cmd_install(args):
    platform_name = args.platform or "claude"
    print(f"\nInstalling assignmentsignal for {PLATFORMS.get(platform_name, {}).get('name', platform_name)}...\n")

    installers = {
        "claude": _install_claude,
        "codex": _install_codex,
        "cursor": _install_cursor,
        "gemini": _install_gemini,
        "aider": _install_aider,
    }
    installer = installers.get(platform_name)
    if not installer:
        print(f"  Platform '{platform_name}' not recognized.")
        print(f"  Supported: {', '.join(installers.keys())}")
        return
    installer()

    # Collect student identity once — stored in config so /assignment needs no prompting
    config_file = ASSIGNMENT_DIR / "config.json"
    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except Exception:
            pass

    existing_name = config.get("candidate_name", "")
    existing_email = config.get("candidate_email", "")

    print()
    if existing_name and existing_email:
        print(f"  Identity: {existing_name} <{existing_email}>")
        update = input("  Update? [y/N] ").strip().lower()
        if update != "y":
            print()
            print(f"\n✓ assignmentsignal installed.\n")
            print(f"  Professor/TA: run 'assignment dashboard' to create assignments and review submissions")
            print(f"  Student:      open Claude Code and type /assignment <CODE>\n")
            return

    print("  To skip the name/email prompt during assignments, we'll save your identity now.")
    name = input("  Your name: ").strip()
    email = input("  Your email: ").strip()

    if name or email:
        if name:
            config["candidate_name"] = name
        if email:
            config["candidate_email"] = email
        ASSIGNMENT_DIR.mkdir(parents=True, exist_ok=True)
        tmp = config_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(config, indent=2))
        tmp.rename(config_file)
        os.chmod(config_file, 0o600)
        print(f"  ✓ Identity saved.")

    print(f"\n✓ assignmentsignal installed.\n")
    print(f"  Professor/TA: run 'assignment dashboard' to create assignments and review submissions")
    print(f"  Student:      open Claude Code and type /assignment <CODE>\n")


def cmd_uninstall(args):
    platform_name = args.platform or "claude"
    if platform_name == "claude":
        cfg = PLATFORMS["claude"]
        skill_dir = cfg["skill_dir"]
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            print(f"  ✓ Skill removed: {skill_dir}")

        submit_skill_dir = Path.home() / ".claude" / "skills" / "submit"
        if submit_skill_dir.exists():
            shutil.rmtree(submit_skill_dir)
            print(f"  ✓ Skill removed: {submit_skill_dir}")

        # Remove hooks from settings.json
        settings_json = cfg["settings_json"]
        if settings_json.exists():
            try:
                settings = json.loads(settings_json.read_text())
                hooks = settings.get("hooks", {})
                for hook_type in ["PreToolUse", "PostToolUse", "Stop"]:
                    hooks.pop(hook_type, None)
                settings_json.write_text(json.dumps(settings, indent=2))
                print(f"  ✓ Hooks removed from {settings_json}")
            except Exception as e:
                print(f"  ⚠ Could not update settings.json: {e}")

        print(f"\n✓ assignmentsignal uninstalled.")


def cmd_configure_email(args):
    from assignment.core.email_sender import configure_email_interactive
    configure_email_interactive()


def cmd_configure_relay(args):
    """
    Configure how assignment sessions are delivered to the professor/TA.

    Three options:
      1. Hosted relay  — relay.assignmentsignal.dev (shared, free to try)
      2. Your own relay — Railway / Render / self-hosted (private, ~$5/mo)
      3. Email only    — SMTP, no server needed (free, manual workflow)
    """
    config_file = Path.home() / ".assignment" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except Exception:
            pass

    current_url     = config.get("relay_url", "")
    current_hm_key  = config.get("hm_key", "")
    current_mode    = "relay" if current_url else ("email" if config.get("smtp_host") else "none")

    print("\nHow do you want to deliver assignment sessions?")
    print("─" * 50)
    print("  1. Your own relay  Railway / Render / self-hosted — private, ~$5/mo")
    print("  2. Email only      SMTP — no server, reports arrive by email")
    print()

    current_label = {"relay": "1", "email": "2", "none": "1"}.get(current_mode, "1")
    choice = input(f"Choice [{current_label}]: ").strip() or current_label

    if choice == "1":
        # ── Self-hosted / own relay ───────────────────────────────────────────
        print()
        print("  Enter your relay URL (Railway / Render / your own server).")
        print()
        prompt = f"Relay URL [{current_url}]: " if current_url else "Relay URL: "
        relay_url = input(prompt).strip().rstrip("/") or current_url

        if not relay_url:
            print("\n  No URL entered — no changes made.\n")
            return

        # Add https:// if user forgot the scheme
        if relay_url and "://" not in relay_url:
            relay_url = "https://" + relay_url

        print("\nRelay API key — only needed if you set RELAY_API_KEY on your server.")
        api_key = input("API key [blank]: ").strip()

        config["relay_url"] = relay_url
        if api_key:
            config["relay_api_key"] = api_key
        config.pop("smtp_host", None)

        config_file.write_text(json.dumps(config, indent=2))
        os.chmod(config_file, 0o600)

        if current_hm_key and current_url == relay_url:
            key_preview = current_hm_key[:8] + "..."
            print(f"\n✓ Relay configured: {relay_url}")
            print(f"  hm_key: {key_preview} (already registered)\n")
        else:
            print(f"\n  Registering with relay...")
            _register_relay(relay_url, config, config_file)

    elif choice == "2":
        # ── Email only ────────────────────────────────────────────────────────
        config.pop("relay_url", None)
        config.pop("hm_key", None)
        config.pop("relay_api_key", None)

        config_file.write_text(json.dumps(config, indent=2))
        os.chmod(config_file, 0o600)

        print(f"\n✓ Email mode selected.")
        print(f"  Sessions will be sent by SMTP when students run /submit.")
        print(f"  Run 'assignment configure-email' to set up your SMTP credentials.\n")

    else:
        print(f"\n  Unknown choice '{choice}' — no changes made.\n")


def _register_relay(relay_url: str, config: dict, config_file: Path):
    """Attempt to register with the relay and store the hm_key. Shared helper."""
    try:
        from assignment.core.transport import RelayTransport, set_hm_key
        hm_key = RelayTransport.register_hm(relay_url)
        set_hm_key(hm_key)
        key_preview = hm_key[:8] + "..."
        print(f"✓ Relay configured: {relay_url}")
        print(f"  hm_key: {key_preview} — your sessions are private to you")
        print(f"  Run 'assignment dashboard' to review students\n")
    except Exception as e:
        print(f"  ⚠ Could not register: {e}")
        print(f"  Relay URL saved. Re-run 'assignment configure-relay' once the relay is reachable.\n")


def cmd_configure_api_key(args):
    """Store OpenAI API key in ~/.assignment/config.json (direct access shortcut)."""
    import getpass
    config_file = Path.home() / ".assignment" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except Exception:
            pass

    print("\nConfigure OpenAI API key for assignmentsignal grading")
    print("─" * 50)
    print("Get your key at: https://platform.openai.com/api-keys")
    print("Enterprise / proxy users: run 'assignment configure-llm' instead.\n")

    key = getpass.getpass("OpenAI API key (sk-...): ").strip()
    if not key.startswith("sk-"):
        print("⚠ Key doesn't look right — should start with 'sk-'. Saved anyway.")

    config["openai_api_key"] = key
    config_file.write_text(json.dumps(config, indent=2))
    os.chmod(config_file, 0o600)
    print(f"\n✓ API key saved to {config_file}")
    print(f"  You can also set OPENAI_API_KEY environment variable instead.\n")


def cmd_configure_llm(args):
    """
    Configure the LLM endpoint used for grading.

    Covers three deployment patterns:
      Direct      — OpenAI API key, default base URL
      Enterprise  — Internal proxy (Floodgate, Azure AI, Bedrock gateway…)
                    Same API shape, different URL + optional custom headers.
    """
    config_file = Path.home() / ".assignment" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except Exception:
            pass

    current_url    = config.get("openai_base_url", "") or config.get("anthropic_base_url", "")
    current_model  = config.get("grading_model", "")
    current_hdrs   = json.dumps(config.get("openai_extra_headers") or config.get("anthropic_extra_headers") or {})

    print("\nConfigure LLM endpoint for assignmentsignal grading")
    print("─" * 55)
    print("Direct (default):    leave Base URL blank, enter OpenAI key")
    print("Enterprise proxy:    enter your proxy URL; API key optional")
    print()

    # ── Base URL ──────────────────────────────────────────────────────────────
    prompt = f"Base URL [{current_url or 'https://api.openai.com'}]: "
    base_url = input(prompt).strip().rstrip("/")
    if not base_url:
        base_url = current_url  # keep existing or leave blank (= use default)

    # ── API key ───────────────────────────────────────────────────────────────
    import getpass
    if base_url and base_url != "https://api.openai.com":
        print("\nAPI key — leave blank if your proxy handles auth (e.g. SSO / network-level).")
    else:
        print("\nGet your OpenAI key at: platform.openai.com/api-keys")
    key = getpass.getpass("API key [blank = keep existing / not required]: ").strip()

    # ── Model override ────────────────────────────────────────────────────────
    default_model = "gpt-5.5"
    print(f"\nModel name — your proxy may use a different alias or version ID.")
    model = input(f"Model [{current_model or default_model}]: ").strip() or current_model

    # ── Extra headers ─────────────────────────────────────────────────────────
    print(f"\nExtra headers — JSON dict for team/project routing (e.g. X-Team-ID).")
    print(f"  Example: {{\"X-Team-ID\": \"ml-hiring\", \"X-Project\": \"assignments\"}}")
    hdrs_raw = input(f"Extra headers [{current_hdrs}]: ").strip() or current_hdrs
    try:
        extra_headers = json.loads(hdrs_raw) if hdrs_raw and hdrs_raw != "{}" else {}
    except Exception:
        print("  ⚠ Could not parse headers as JSON — ignoring.")
        extra_headers = config.get("openai_extra_headers") or {}

    # ── Save ──────────────────────────────────────────────────────────────────
    if base_url:
        config["openai_base_url"] = base_url
    if key:
        config["openai_api_key"] = key
    if model and model != default_model:
        config["grading_model"] = model
    elif "grading_model" in config and not model:
        del config["grading_model"]
    if extra_headers:
        config["openai_extra_headers"] = extra_headers
    elif "openai_extra_headers" in config:
        del config["openai_extra_headers"]

    config_file.write_text(json.dumps(config, indent=2))
    os.chmod(config_file, 0o600)

    # ── Summary ───────────────────────────────────────────────────────────────
    effective_url = base_url or "https://api.openai.com"
    effective_model = model or default_model
    key_display = (key[:8] + "...") if key else "(none — proxy handles auth)"
    print(f"\n✓ LLM grading configured:")
    print(f"  Base URL:  {effective_url}")
    print(f"  API key:   {key_display}")
    print(f"  API:       OpenAI Responses")
    print(f"  Model:     {effective_model}")
    if extra_headers:
        print(f"  Headers:   {json.dumps(extra_headers)}")
    print()


def cmd_configure_github_app(args):
    """
    Configure GitHub OAuth for the relay server.

    This is for relay operators — not students. Sets GITHUB_CLIENT_ID and
    GITHUB_CLIENT_SECRET env vars that the relay reads at startup.

    How to create a GitHub OAuth App:
      1. GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
      2. Application name:  assignmentsignal (or your company name)
      3. Homepage URL:      your relay URL  (e.g. https://relay.example.com)
      4. Callback URL:      <relay_url>/auth/github/callback
      5. Click Register Application
      6. Copy Client ID and generate a Client Secret
    """
    print("\nConfigure GitHub OAuth for the relay server")
    print("─" * 52)
    print("Create an OAuth App at: github.com/settings/developers")
    print("Callback URL: <your_relay_url>/auth/github/callback\n")

    client_id = input("GitHub Client ID: ").strip()
    if not client_id:
        print("\n  No Client ID entered — no changes made.\n")
        return

    import getpass
    client_secret = getpass.getpass("GitHub Client Secret: ").strip()
    if not client_secret:
        print("\n  No Client Secret entered — no changes made.\n")
        return

    relay_base = input("Your relay base URL (e.g. https://relay.example.com): ").strip().rstrip("/")

    print("\n  Set these environment variables on your relay server:\n")
    print(f"  GITHUB_CLIENT_ID={client_id}")
    print(f"  GITHUB_CLIENT_SECRET={client_secret}")
    if relay_base:
        print(f"  RELAY_BASE_URL={relay_base}")
    print()
    print("  Railway / Render: add them in the Variables / Environment tab.")
    print("  Docker:           add them to your docker-compose.yml or .env file.")

    # Also save to local config for self-hosted single-machine deployments
    config_file = Path.home() / ".assignment" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except Exception:
            pass
    config["github_client_id"]     = client_id
    config["github_client_secret"] = client_secret
    if relay_base:
        config["relay_base_url"] = relay_base
    config_file.write_text(json.dumps(config, indent=2))
    os.chmod(config_file, 0o600)
    print(f"\n✓ Also saved to {config_file} for local relay deployments.\n")


def cmd_dashboard(args):
    from assignment.dashboard.serve import start_dashboard
    start_dashboard(getattr(args, "code", None))


def cmd_status(args):
    from assignment.core.session import get_session_status
    status = get_session_status()
    if status:
        tl_str = ""
        if status.get("time_limit_minutes"):
            remaining = status["time_limit_minutes"] - status["elapsed_minutes"]
            tl_str = f" | {max(0, round(remaining, 1))}min remaining"
        print(f"\n  Active session: {status['code']}")
        print(f"  Elapsed: {status['elapsed_minutes']} minutes{tl_str}")
        print(f"  Events captured: {status['event_count']}")
        print(f"\n  Type /submit to end the session.\n")
    else:
        print(f"\n  No active session.\n")


def main():
    parser = argparse.ArgumentParser(
        prog="assignment",
        description="assignmentsignal — AI-native assignment platform",
    )
    sub = parser.add_subparsers(dest="command")

    p_install = sub.add_parser("install", help="Install skill + hooks")
    p_install.add_argument("--platform", default="claude",
                           choices=["claude", "codex", "cursor", "gemini", "aider"],
                           help="AI coding platform to install for")

    p_uninstall = sub.add_parser("uninstall", help="Remove skill + hooks")
    p_uninstall.add_argument("--platform", default="claude")

    sub.add_parser("configure-email", help="Set up SMTP credentials")
    sub.add_parser("configure-api-key", help="Store OpenAI API key (direct access)")
    sub.add_parser("configure-llm", help="Configure LLM endpoint for grading (enterprise proxies, custom base URL)")
    sub.add_parser("configure-relay", help="Set relay server URL and API key")
    p_dashboard = sub.add_parser("dashboard", help="Open professor/TA dashboard")
    p_dashboard.add_argument("code", nargs="?", default=None, help="Jump directly to a student submission (e.g. ASG-1234-AB)")
    sub.add_parser("status", help="Show active session status")

    # Relay operator command — run once when deploying the relay.
    sub.add_parser("configure-github-app", help="Print GitHub OAuth relay environment variables")

    args = parser.parse_args()

    if args.command == "install":
        cmd_install(args)
    elif args.command == "uninstall":
        cmd_uninstall(args)
    elif args.command == "configure-email":
        cmd_configure_email(args)
    elif args.command == "configure-api-key":
        cmd_configure_api_key(args)
    elif args.command == "configure-llm":
        cmd_configure_llm(args)
    elif args.command == "configure-relay":
        cmd_configure_relay(args)
    elif args.command == "configure-github-app":
        cmd_configure_github_app(args)
    elif args.command == "dashboard":
        cmd_dashboard(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
