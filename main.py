"""Launcher to run backend (FastAPI/uvicorn) and frontend (npm) together.

Behavior:
- Start backend using the current Python executable (ensures venv is used when available):
  python -m uvicorn backend.blood_bank_fastapi:app --host 127.0.0.1 --port 8000
- Wait for the backend health endpoint (http://127.0.0.1:8000/) to return HTTP 200.
- Start frontend with `npm start` in the `frontend` folder.
- Stream stdout/stderr from both processes, prefixing lines with BACKEND/FRONTEND.
- If one process exits or on Ctrl+C, terminate both cleanly.

This avoids the React dev server proxy ECONNREFUSED errors by ensuring the
backend is up before the frontend starts.
"""

from __future__ import annotations

import os
import sys
import time
import threading
import subprocess
from typing import Optional
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
BACKEND_MODULE = "backend.blood_bank_fastapi:app"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
HEALTH_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}/"


def stream_process_output(proc: subprocess.Popen, prefix: str) -> None:
    """Read process stdout/stderr and print lines with a prefix."""

    def _reader(pipe, name):
        try:
            with pipe:
                for line in iter(pipe.readline, b""):
                    try:
                        text = line.decode(errors="replace").rstrip()
                    except Exception:
                        text = str(line)
                    print(f"[{prefix}] {text}")
        except Exception as exc:  # defensive
            print(f"[{prefix}] error reading {name}: {exc}")

    if proc.stdout:
        threading.Thread(target=_reader, args=(proc.stdout, "stdout"), daemon=True).start()
    if proc.stderr:
        threading.Thread(target=_reader, args=(proc.stderr, "stderr"), daemon=True).start()


def wait_for_health(url: str, timeout: int = 30, interval: float = 0.5) -> bool:
    """Poll the given URL until it responds with HTTP 200 or timeout (seconds).

    Returns True if healthy, False if timed out.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as resp:
                code = getattr(resp, "getcode", lambda: None)()
                if code == 200 or code is None:
                    return True
        except HTTPError as e:
            # server responded but not 200 yet; treat as not ready
            print(f"[HEALTH] HTTPError {e.code}; waiting...")
        except URLError:
            pass
        except Exception:
            pass
        time.sleep(interval)
    return False


def kill_process(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def start_backend(python_executable: str = sys.executable, host: str = BACKEND_HOST, port: int = BACKEND_PORT) -> subprocess.Popen:
    cmd = [python_executable, "-m", "uvicorn", BACKEND_MODULE, "--host", host, "--port", str(port), "--reload"]
    print(f"[LAUNCHER] Starting backend: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stream_process_output(proc, "BACKEND")
    return proc


def start_frontend(cwd: Optional[str] = FRONTEND_DIR) -> subprocess.Popen:
    # On Windows the npm executable is typically available as npm.cmd when
    # launched from non-shell contexts; using shell=True with the string
    # command also lets the OS resolve it. Try a few fallbacks and provide
    # a helpful error if none work.
    print(f"[LAUNCHER] Starting frontend in {cwd}: npm start")
    if os.name == "nt":
        # Try running via the shell first (cmd.exe) which should resolve npm
        try:
            proc = subprocess.Popen("npm start", cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        except FileNotFoundError:
            # Fallback to npm.cmd explicitly
            try:
                proc = subprocess.Popen(["npm.cmd", "start"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except FileNotFoundError as e:
                raise FileNotFoundError("npm not found. Ensure Node.js/npm is installed and 'npm' is on your PATH.") from e
    else:
        try:
            proc = subprocess.Popen(["npm", "start"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError as e:
            raise FileNotFoundError("npm not found. Ensure Node.js/npm is installed and 'npm' is on your PATH.") from e

    stream_process_output(proc, "FRONTEND")
    return proc


def main():
    backend_proc: Optional[subprocess.Popen] = None
    frontend_proc: Optional[subprocess.Popen] = None
    try:
        backend_proc = start_backend()

        print(f"[LAUNCHER] Waiting up to 30s for backend health at {HEALTH_URL}...")
        healthy = wait_for_health(HEALTH_URL, timeout=30)
        if not healthy:
            print(f"[LAUNCHER] Backend did not become healthy within timeout. Check logs above.")
            # Let the backend logs guide the user; still attempt to start frontend if they insist
            # but by default we stop here.
            # Kill backend and exit with error.
            if backend_proc:
                kill_process(backend_proc)
            sys.exit(1)

        print("[LAUNCHER] Backend is healthy — starting frontend now.")
        frontend_proc = start_frontend()

        # Wait until one process exits; then shut down the other.
        while True:
            if backend_proc and backend_proc.poll() is not None:
                print(f"[LAUNCHER] Backend exited with {backend_proc.returncode}; stopping frontend")
                if frontend_proc and frontend_proc.poll() is None:
                    kill_process(frontend_proc)
                break
            if frontend_proc and frontend_proc.poll() is not None:
                print(f"[LAUNCHER] Frontend exited with {frontend_proc.returncode}; stopping backend")
                if backend_proc and backend_proc.poll() is None:
                    kill_process(backend_proc)
                break
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("[LAUNCHER] KeyboardInterrupt received — terminating processes")
        if frontend_proc and frontend_proc.poll() is None:
            kill_process(frontend_proc)
        if backend_proc and backend_proc.poll() is None:
            kill_process(backend_proc)
    finally:
        print("[LAUNCHER] Done.")


if __name__ == "__main__":
    main()
