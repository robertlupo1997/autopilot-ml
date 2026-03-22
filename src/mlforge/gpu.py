"""GPU auto-detection for deep learning and fine-tuning domains."""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def detect_gpu() -> dict | None:
    """Detect available GPU via torch.cuda or nvidia-smi fallback.

    Returns:
        Dict with gpu info (name, memory_gb, cuda_version), or None if no GPU.
    """
    # Try torch first
    try:
        import torch

        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            return {
                "name": props.name,
                "memory_gb": round(props.total_mem / (1024**3), 1),
                "cuda_version": torch.version.cuda or "unknown",
            }
        return None
    except ImportError:
        pass

    # Fallback: nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            return {
                "name": parts[0],
                "memory_gb": round(float(parts[1]) / 1024, 1) if len(parts) > 1 else 0,
                "cuda_version": "unknown",
            }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def check_gpu_for_domain(domain: str) -> None:
    """Log GPU status for domains that benefit from GPU acceleration."""
    if domain not in ("deeplearning", "finetuning"):
        return

    gpu = detect_gpu()
    if gpu:
        logger.info("GPU detected: %s (%.1f GB, CUDA %s)", gpu["name"], gpu["memory_gb"], gpu["cuda_version"])
    else:
        logger.warning(
            "No GPU detected for %s domain. Training will be slow on CPU. "
            "Install CUDA and PyTorch with GPU support for better performance.",
            domain,
        )
