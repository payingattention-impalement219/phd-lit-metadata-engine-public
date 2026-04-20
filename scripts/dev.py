#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def command_exists(command: str) -> bool:
    return subprocess.call(["/usr/bin/env", "which", command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def module_exists(module: str) -> bool:
    return subprocess.call([sys.executable, "-c", f"import {module}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def main() -> int:
    if sys.version_info < (3, 10):
        print("This app needs Python 3.10 or newer.")
        print("Your current interpreter is:", sys.executable)
        print("Recreate the virtual environment with Homebrew Python:")
        print("  deactivate 2>/dev/null || true")
        print("  rm -rf .venv")
        print("  python3.12 -m venv .venv")
        print("  source .venv/bin/activate")
        print("  python -m pip install --upgrade pip setuptools wheel")
        print("  pip install -e './backend[dev]'")
        return 1

    if not command_exists("npm"):
        print("npm is required for the React frontend. Install Node.js first.")
        print("With Homebrew: brew install node")
        return 1

    if not module_exists("uvicorn"):
        print("Missing backend dependency: uvicorn")
        print("Install the backend into the active virtual environment:")
        print("  source .venv/bin/activate")
        print("  python -m pip install --upgrade pip setuptools wheel")
        print("  pip install -e './backend[dev]'")
        return 1

    env = os.environ.copy()
    env.setdefault("APP_HOST", "127.0.0.1")
    env.setdefault("APP_PORT", "8000")

    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
        cwd=BACKEND,
        env=env,
    )
    frontend = subprocess.Popen(["npm", "run", "dev", "--", "--host", "127.0.0.1"], cwd=FRONTEND, env=env)

    print("Backend:  http://127.0.0.1:8000/docs")
    print("Frontend: http://127.0.0.1:5173")
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5173")

    try:
        while backend.poll() is None and frontend.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping local app...")
    finally:
        for process in (frontend, backend):
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
        for process in (frontend, backend):
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
