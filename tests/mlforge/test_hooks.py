"""Tests for hook settings and guard script generation."""

from __future__ import annotations

import json
import os
import stat

from mlforge.hooks import generate_guard_script, generate_hook_settings, write_hook_files

FROZEN = ["prepare.py", "forecast.py"]


class TestGenerateHookSettings:
    """Verify settings.json structure."""

    def test_generate_hook_settings_structure(self):
        settings = generate_hook_settings(FROZEN)
        assert "permissions" in settings
        assert "hooks" in settings

    def test_hook_settings_deny_frozen(self):
        settings = generate_hook_settings(FROZEN)
        deny = settings["permissions"]["deny"]
        # Each frozen file should have Edit and Write denied
        for frozen_file in FROZEN:
            found = False
            for entry in deny:
                if frozen_file in entry.get("path", ""):
                    found = True
                    break
            assert found, f"{frozen_file} not denied in settings"

    def test_hook_settings_pretooluse_matcher(self):
        settings = generate_hook_settings(FROZEN)
        hooks = settings["hooks"]
        assert "PreToolUse" in hooks
        pre_tool = hooks["PreToolUse"]
        # Should have at least one hook matching Edit|Write
        assert len(pre_tool) > 0
        hook = pre_tool[0]
        assert "Edit" in hook["matcher"] or "Write" in hook["matcher"]


class TestGenerateGuardScript:
    """Verify guard script content."""

    def test_guard_script_contains_frozen_files(self):
        script = generate_guard_script(FROZEN)
        for frozen_file in FROZEN:
            assert frozen_file in script

    def test_generate_guard_script_denies_frozen(self):
        """Script should contain DENY JSON format for frozen files."""
        script = generate_guard_script(FROZEN)
        # The script should reference a deny/block pattern
        assert "FROZEN_FILES" in script
        assert "prepare.py" in script
        assert "forecast.py" in script

    def test_generate_guard_script_has_shebang(self):
        script = generate_guard_script(FROZEN)
        assert script.startswith("#!/bin/bash")

    def test_generate_guard_script_allows_non_frozen(self):
        """Script logic: non-frozen files should not appear in deny list."""
        script = generate_guard_script(FROZEN)
        # "train.py" is not frozen, should not be in FROZEN_FILES variable
        assert "train.py" not in script


class TestWriteHookFiles:
    """Verify file creation and permissions."""

    def test_write_hook_files_creates_settings(self, tmp_path):
        write_hook_files(tmp_path, FROZEN)
        settings_path = tmp_path / ".claude" / "settings.json"
        assert settings_path.exists()
        # Verify it's valid JSON
        data = json.loads(settings_path.read_text())
        assert "permissions" in data

    def test_write_hook_files_creates_guard_script(self, tmp_path):
        write_hook_files(tmp_path, FROZEN)
        guard_path = tmp_path / ".claude" / "hooks" / "guard-frozen.sh"
        assert guard_path.exists()

    def test_guard_script_is_executable(self, tmp_path):
        write_hook_files(tmp_path, FROZEN)
        guard_path = tmp_path / ".claude" / "hooks" / "guard-frozen.sh"
        mode = os.stat(guard_path).st_mode
        assert mode & stat.S_IXUSR, "Script should be executable by owner"
        assert mode & stat.S_IXGRP, "Script should be executable by group"
        assert mode & stat.S_IXOTH, "Script should be executable by others"
