"""Unit tests for swarm_claims -- TTL-based experiment dedup."""

import time
from pathlib import Path

import pytest

from automl.swarm_claims import try_claim, release_claim, CLAIM_TTL


class TestTryClaim:
    def test_first_claim_succeeds(self, tmp_path):
        """try_claim returns True when no active claim exists."""
        result = try_claim(tmp_path, "agent-0", "train LogisticRegression")
        assert result is True

    def test_duplicate_blocked_within_ttl(self, tmp_path):
        """try_claim returns False when another agent has an active (non-expired) claim."""
        try_claim(tmp_path, "agent-0", "train LogisticRegression")
        result = try_claim(tmp_path, "agent-1", "train LogisticRegression")
        assert result is False

    def test_same_agent_duplicate_blocked(self, tmp_path):
        """Same agent trying to claim the same description twice is blocked."""
        try_claim(tmp_path, "agent-0", "train LogisticRegression")
        result = try_claim(tmp_path, "agent-0", "train LogisticRegression")
        assert result is False

    def test_different_description_allowed(self, tmp_path):
        """Different description produces a different key, so claim succeeds."""
        try_claim(tmp_path, "agent-0", "train LogisticRegression")
        result = try_claim(tmp_path, "agent-1", "train RandomForest")
        assert result is True

    def test_claim_creates_file(self, tmp_path):
        """try_claim writes a JSON claim file in claims_dir."""
        try_claim(tmp_path, "agent-0", "train LogisticRegression")
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1


class TestTTLExpiry:
    def test_expired_claim_allows_reclaim(self, tmp_path, monkeypatch):
        """Expired claim (age > CLAIM_TTL) allows re-claiming by any agent."""
        # Plant a claim with a timestamp in the past
        import hashlib, json
        description = "train XGBoost baseline"
        key = hashlib.md5(description.encode()).hexdigest()[:8]
        claim_path = tmp_path / f"agent-0--{key}.json"
        expired_time = time.time() - CLAIM_TTL - 1  # 1 second past expiry
        claim_path.write_text(json.dumps({
            "agent_id": "agent-0",
            "description": description,
            "claimed_at": expired_time,
        }))

        # New agent should succeed -- old claim has expired
        result = try_claim(tmp_path, "agent-1", description)
        assert result is True

    def test_active_claim_blocks(self, tmp_path):
        """Active claim (age < CLAIM_TTL) blocks re-claiming."""
        description = "train RandomForest"
        try_claim(tmp_path, "agent-0", description)
        result = try_claim(tmp_path, "agent-1", description)
        assert result is False


class TestReleaseClaim:
    def test_release_removes_file(self, tmp_path):
        """release_claim removes the claim file."""
        description = "train LightGBM"
        try_claim(tmp_path, "agent-0", description)
        files_before = list(tmp_path.glob("*.json"))
        assert len(files_before) == 1

        release_claim(tmp_path, "agent-0", description)
        files_after = list(tmp_path.glob("*.json"))
        assert len(files_after) == 0

    def test_release_no_error_when_missing(self, tmp_path):
        """release_claim does not raise when claim file does not exist."""
        # Should not raise any exception
        release_claim(tmp_path, "agent-0", "nonexistent description")

    def test_release_allows_reclaim(self, tmp_path):
        """After release, another agent can claim the same description."""
        description = "train ElasticNet"
        try_claim(tmp_path, "agent-0", description)
        release_claim(tmp_path, "agent-0", description)
        result = try_claim(tmp_path, "agent-1", description)
        assert result is True
