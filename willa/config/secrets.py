"""
Load secrets for Willa configuration.
"""

from pathlib import Path


def load_from_run_secrets() -> dict[str, str]:
    """Load all values from ``/run/secrets``.

    :returns: A dictionary of variable names and secret contents.
    :rtype: dict[str, str]
    """
    run_dir = Path('/run/secrets')
    if not run_dir.exists() or not run_dir.is_dir():
        return {}

    secrets: dict[str, str] = {}
    for item in run_dir.iterdir():
        if not item.is_file():
            continue

        secrets[item.name] = item.read_text('utf-8')

    return secrets
