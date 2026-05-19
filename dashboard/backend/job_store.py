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
        }
    return jid


def log_job(jid: str, message: str):
    with _lock:
        if jid in _jobs:
            _jobs[jid]["logs"].append({"ts": round(time.time(), 3), "msg": message})


def complete_job(jid: str, result: str):
    with _lock:
        if jid in _jobs:
            _jobs[jid]["status"] = "done"
            _jobs[jid]["result"] = result
            _jobs[jid]["finished"] = time.time()


def fail_job(jid: str, error: str):
    with _lock:
        if jid in _jobs:
            _jobs[jid]["status"] = "error"
            _jobs[jid]["error"] = error
            _jobs[jid]["finished"] = time.time()


def get_job(jid: str) -> dict | None:
    with _lock:
        return _jobs.get(jid)


def list_jobs() -> list:
    with _lock:
        return sorted(_jobs.values(), key=lambda j: j["started"], reverse=True)
