"""Convenience entry point for launching the LiveKit voice agent.

This thin wrapper mirrors the behaviour of the ``lk-agents`` console script
shipped with ``livekit-agents``.  It exists purely as a fallback for
environments where the console script is not on ``PATH`` (for example when a
virtual environment's ``Scripts/`` or ``bin/`` directory has not been exported).
"""
from __future__ import annotations

from livekit.agents import WorkerOptions
from livekit.agents.cli import run_app

from backend.app.services.voice_agent import run_agent


def main() -> None:
    """Delegate to ``livekit.agents``' CLI using the project entry point."""

    options = WorkerOptions(entrypoint_fnc=run_agent)
    run_app(options)


if __name__ == "__main__":  # pragma: no cover - exercised manually
    main()
