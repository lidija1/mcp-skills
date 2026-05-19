"""
Shared in-process job store.

Imported by both main.py and chat_router.py so that chat-dispatched jobs
appear in the Jobs panel sidebar. Python's module cache guarantees that _jobs
is the same dict object in all importers within a single process.
"""
import time
import uuid
import threading

_jobs: dict = {}
_lock = threading.Lock()


def new_job(label: str) -> str:
    jid = str(uuid.uuid4())[:8]
    with _lock:
        _jobs[jid] = {
            "id": jid,
            "label": label,
            "status": "running",
            "result": None,
            "error": None,
            "started": time.time(),
            "finished": None,
            "logs": [],
            "current_status": None,
        }
    return jid


def log_job(jid: str, message: str):
    with _lock:
        if jid in _jobs:
            _jobs[jid]["logs"].append({"ts": round(time.time(), 3), "msg": message})


def update_job_status(jid: str, phase: str, detail: str | None = None):
    now = time.time()
    with _lock:
        job = _jobs.get(jid)
        if not job:
            return
        started = float(job.get("started") or now)
        job["current_status"] = {
            "phase": phase,
            "detail": detail or "",
            "updated": now,
            "elapsed_s": round(max(0, now - started), 1),
        }


def complete_job(jid: str, result: str):
    with _lock:
        if jid in _jobs:
            _jobs[jid]["status"] = "done"
            _jobs[jid]["result"] = result
            _jobs[jid]["finished"] = time.time()
            _jobs[jid]["current_status"] = None


def fail_job(jid: str, error: str):
    with _lock:
        if jid in _jobs:
            _jobs[jid]["status"] = "error"
            _jobs[jid]["error"] = error
            _jobs[jid]["finished"] = time.time()
            _jobs[jid]["current_status"] = None


def get_job(jid: str) -> dict | None:
    with _lock:
        return _jobs.get(jid)


def list_jobs() -> list:
    with _lock:
        return sorted(_jobs.values(), key=lambda j: j["started"], reverse=True)
