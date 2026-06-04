import time
import uuid
import threading

import dashboard_db

_jobs: dict = {}
_lock = threading.Lock()
_cancel_flags: dict[str, bool] = {}

def cancel_job(jid: str):
    with _lock:
        _cancel_flags[jid] = True

def is_canceled(jid: str) -> bool:
    with _lock:
        return _cancel_flags.get(jid, False)

def clear_cancel(jid: str):
    with _lock:
        _cancel_flags.pop(jid, None)

def _job_already_canceled(jid: str) -> bool:
    if is_canceled(jid):
        return True
    with _lock:
        job = _jobs.get(jid)
        if job and job.get("status") == "canceled":
            return True
    persisted = dashboard_db.get_execution(jid)
    return bool(persisted and persisted.get("status") == "canceled")

def mark_canceled(jid: str):
    dashboard_db.finish_execution(jid, "canceled", error="Canceled by user")

    with _lock:
        if jid in _jobs:
            _jobs[jid]["status"] = "canceled"
            _jobs[jid]["error"] = "Canceled by user"
            _jobs[jid]["finished"] = time.time()
            _jobs[jid]["current_status"] = None

def new_job(label: str, execution_type: str = "job", created_by: int | None = None, metadata: dict | None = None) -> str:
    jid = str(uuid.uuid4())[:8]
    dashboard_db.create_execution(
        jid,
        execution_name=label,
        execution_type=execution_type,
        created_by=created_by,
        metadata=metadata,
    )
    with _lock:
        _jobs[jid] = dashboard_db.get_execution(jid) or {
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
    dashboard_db.append_execution_log(jid, message)
    with _lock:
        if jid in _jobs:
            _jobs[jid]["logs"].append({"ts": round(time.time(), 3), "msg": message})


def update_job_status(jid: str, phase: str, detail: str | None = None):
    if _job_already_canceled(jid):
        return
    now = time.time()
    dashboard_db.update_execution_status(jid, phase, detail or "")
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
    if _job_already_canceled(jid):
        return
    dashboard_db.finish_execution(jid, "done", result=result)
    with _lock:
        if jid in _jobs:
            _jobs[jid]["status"] = "done"
            _jobs[jid]["result"] = result
            _jobs[jid]["finished"] = time.time()
            _jobs[jid]["current_status"] = None


def fail_job(jid: str, error: str):
    if _job_already_canceled(jid):
        return
    dashboard_db.finish_execution(jid, "error", error=error)
    with _lock:
        if jid in _jobs:
            _jobs[jid]["status"] = "error"
            _jobs[jid]["error"] = error
            _jobs[jid]["finished"] = time.time()
            _jobs[jid]["current_status"] = None


def get_job(jid: str, user: dict | None = None) -> dict | None:
    persisted = dashboard_db.get_execution(jid, user=user)
    if persisted:
        with _lock:
            _jobs[jid] = persisted
        return persisted
    with _lock:
        return _jobs.get(jid)


def list_jobs(user: dict | None = None) -> list:
    persisted = dashboard_db.list_executions(user=user)
    if persisted:
        with _lock:
            for job in persisted:
                _jobs[job["id"]] = job
        return persisted
    with _lock:
        return sorted(_jobs.values(), key=lambda j: j["started"], reverse=True)


def delete_job(jid: str, user: dict | None = None) -> bool:
    deleted = dashboard_db.delete_execution(jid, user=user)
    if deleted:
        with _lock:
            _jobs.pop(jid, None)
            _cancel_flags.pop(jid, None)
    return deleted
