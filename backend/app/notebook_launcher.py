from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from .config import NOTEBOOK_PATH, PROJECT_DIR
from .models import NotebookStatus


LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


def notebook_status() -> NotebookStatus:
    jupyter = _find_command("jupyter")
    vscode = _find_command("code")
    message_parts = []
    if not jupyter:
        message_parts.append("Jupyter is not on PATH. Install jupyterlab in the Python environment.")
    if not vscode:
        message_parts.append("VS Code 'code' CLI is not on PATH. Enable it from VS Code command palette.")
    return NotebookStatus(
        notebook_path=str(NOTEBOOK_PATH),
        jupyter_available=bool(jupyter),
        vscode_available=bool(vscode),
        jupyter_command=jupyter or "",
        vscode_command=vscode or "",
        message=" ".join(message_parts) or "Notebook launchers are ready.",
    )


def ensure_notebook_exists() -> None:
    if not NOTEBOOK_PATH.exists():
        raise FileNotFoundError(f"Notebook not found: {NOTEBOOK_PATH}")


def _find_command(command: str) -> str | None:
    candidates = [
        shutil.which(command),
        str(PROJECT_DIR / ".venv" / "bin" / command),
        f"/opt/homebrew/bin/{command}",
        f"/usr/local/bin/{command}",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists() and os.access(candidate, os.X_OK):
            return candidate
    return None


def open_jupyter() -> dict[str, str]:
    try:
        ensure_notebook_exists()
    except FileNotFoundError as exc:
        return {"status": "unavailable", "message": str(exc)}
    jupyter = _find_command("jupyter")
    if not jupyter:
        return {
            "status": "unavailable",
            "message": "Jupyter is not installed in the active environment. Run: source .venv/bin/activate && pip install jupyterlab",
        }
    try:
        subprocess.Popen(
            [jupyter, "lab", str(NOTEBOOK_PATH)],
            cwd=PROJECT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return {"status": "unavailable", "message": f"Could not launch Jupyter: {exc}"}
    return {"status": "launching", "message": "Jupyter is opening the analysis notebook."}


def open_vscode() -> dict[str, str]:
    try:
        ensure_notebook_exists()
    except FileNotFoundError as exc:
        return {"status": "unavailable", "message": str(exc)}
    code = _find_command("code")
    if code:
        try:
            subprocess.Popen(
                [code, str(NOTEBOOK_PATH)],
                cwd=PROJECT_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return {"status": "launching", "message": "VS Code is opening the analysis notebook."}
        except OSError as exc:
            return {"status": "unavailable", "message": f"Could not launch VS Code with {code}: {exc}"}
    uri = f"vscode://file/{NOTEBOOK_PATH}"
    return {"status": "unavailable", "message": f"VS Code CLI not found. Try opening this URI manually: {uri}"}


def write_context(job_id: str, export_path: str = "") -> Path:
    path = NOTEBOOK_PATH.parent / "analysis_context.json"
    path.write_text(json.dumps({"job_id": job_id, "export_path": export_path}, indent=2), encoding="utf-8")
    return path
