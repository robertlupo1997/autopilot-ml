"""TTL-based claim files for iteration-phase experiment deduplication.

Prevents two swarm agents from running identical iteration experiments.
Claims expire after CLAIM_TTL seconds -- expired claims allow re-claiming
by any agent (age check at read time, no background daemon needed).

No external dependencies -- stdlib only (hashlib, json, pathlib, time).
"""

import hashlib
import json
import time
from pathlib import Path

CLAIM_TTL = 300  # seconds (5 minutes)


def _claim_key(description: str) -> str:
    """Return first 8 hex chars of MD5 hash of description string."""
    return hashlib.md5(description.encode()).hexdigest()[:8]


def try_claim(claims_dir: Path, agent_id: str, description: str) -> bool:
    """Attempt to claim an experiment idea. Returns True if claim succeeded.

    Checks all existing claim files with the same description hash. If any
    active (non-expired) claim exists, returns False. Otherwise, writes a new
    claim JSON file and returns True.

    A claim is active if its age (time.time() - claimed_at) < CLAIM_TTL.
    Malformed or unreadable claim files are silently skipped.

    Args:
        claims_dir: Directory where claim JSON files are stored.
        agent_id: Identifier for this agent (e.g., "agent-0").
        description: Human-readable experiment description to claim.

    Returns:
        True if this agent now holds the claim; False if another agent
        already holds an active claim for the same description.
    """
    key = _claim_key(description)
    claim_path = claims_dir / f"{agent_id}--{key}.json"
    # Check for any active claim with the same key
    for existing in claims_dir.glob(f"*--{key}.json"):
        try:
            data = json.loads(existing.read_text())
            age = time.time() - data["claimed_at"]
            if age < CLAIM_TTL:
                return False  # active claim exists
        except (json.JSONDecodeError, KeyError, OSError):
            pass  # malformed or deleted -- treat as expired
    # No active claim found -- write our own
    claim_path.write_text(
        json.dumps(
            {
                "agent_id": agent_id,
                "description": description,
                "claimed_at": time.time(),
            }
        )
    )
    return True


def release_claim(claims_dir: Path, agent_id: str, description: str) -> None:
    """Remove the claim file for this agent and description.

    No-op if the claim file does not exist (missing_ok=True).

    Args:
        claims_dir: Directory where claim JSON files are stored.
        agent_id: Identifier for this agent (e.g., "agent-0").
        description: Human-readable experiment description to release.
    """
    key = _claim_key(description)
    claim_path = claims_dir / f"{agent_id}--{key}.json"
    claim_path.unlink(missing_ok=True)
