"""Completion notifications for unattended runs."""

from __future__ import annotations

import json
import logging
import platform
import subprocess
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def send_notification(
    title: str,
    body: str,
    method: str = "desktop",
) -> bool:
    """Send a completion notification.

    Args:
        title: Notification title.
        body: Notification body text.
        method: ``"desktop"`` for OS notifications, or ``"webhook:<url>"``
            for HTTP POST.

    Returns:
        True if notification was sent successfully.
    """
    if method == "desktop":
        return _notify_desktop(title, body)
    elif method.startswith("webhook:"):
        url = method[len("webhook:"):]
        return _notify_webhook(title, body, url)
    else:
        logger.warning("Unknown notification method: %s", method)
        return False


def _notify_desktop(title: str, body: str) -> bool:
    """Send a desktop notification using OS-native tools."""
    system = platform.system()
    try:
        if system == "Linux":
            subprocess.run(
                ["notify-send", title, body],
                capture_output=True, timeout=5,
            )
            return True
        elif system == "Darwin":
            script = f'display notification "{body}" with title "{title}"'
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=5,
            )
            return True
        else:
            logger.debug("Desktop notifications not supported on %s", system)
            return False
    except FileNotFoundError:
        logger.debug("Notification command not found on %s", system)
        return False
    except subprocess.TimeoutExpired:
        return False


def _notify_webhook(title: str, body: str, url: str) -> bool:
    """POST a JSON notification to a webhook URL."""
    payload = json.dumps({"title": title, "body": body}).encode()
    try:
        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10):  # noqa: S310
            pass
        return True
    except Exception:
        logger.debug("Webhook notification failed", exc_info=True)
        return False
