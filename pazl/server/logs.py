"""Activity / error log for analysis: every project event, API error, AI run (tools, usage, errors) and browser
error goes as one JSON line into <DATA>/logs/YYYY-MM-DD.jsonl. report_zip() packs the recent logs, a readable
summary (report.md), the current recipe and the AI usage into one file for download."""
from __future__ import annotations

import io
import json
import platform
import sys
import threading
import time
import traceback
import zipfile
from collections import Counter
from pathlib import Path

from ..paths import DATA

LOG_DIR = DATA / "logs"
_lock = threading.Lock()


def log(kind: str, **data):
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, **data}
    try:
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with _lock:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_DIR / f"{time.strftime('%Y-%m-%d')}.jsonl", "a", encoding="utf-8") as f:
                f.write(line[:20000] + "\n")
    except Exception:  # logging must never break the app
        pass


def log_exception(where: str, ex: BaseException, **data):
    log("error", where=where, error=f"{type(ex).__name__}: {ex}", trace=traceback.format_exc(limit=6), **data)


def _recent(days=7):
    files = sorted(LOG_DIR.glob("*.jsonl"))[-days:]
    recs = []
    for f in files:
        for line in f.read_text("utf-8", errors="replace").splitlines():
            try:
                recs.append(json.loads(line))
            except ValueError:
                pass
    return files, recs


def summary_md(project=None, usage=None) -> str:
    from .. import __version__
    files, recs = _recent()
    kinds = Counter(r.get("kind") for r in recs)
    events = Counter(r.get("type") for r in recs if r.get("kind") == "event")
    errors = [r for r in recs if r.get("kind") in ("error", "client_error") or r.get("type") == "error"
              or (r.get("kind") == "event" and r.get("errors"))]
    lines = [f"# 3dPazl report — {time.strftime('%Y-%m-%d %H:%M')}", "",
             f"- Version: {__version__}; Python {sys.version.split()[0]}; {platform.platform()}",
             f"- Log files: {', '.join(f.name for f in files) or 'none'}; records: {len(recs)}"]
    if project is not None:
        st = project.summary()
        lines += [f"- Project: **{st.get('name')}**, style {st.get('style')}, {st.get('elements')} elements, version {st.get('version')}"]
        v = project.last_validation
        if v:
            lines += [f"- Last check: {'OK' if v.get('ok') else 'PROBLEMS'}; {len(v.get('errors', []))} errors"]
    if usage:
        t = usage.get("total", {})
        lines += ["", "## AI usage (this project)",
                  f"- Runs: {t.get('runs', 0)}; tokens in {t.get('input', 0):,} / out {t.get('output', 0):,}; "
                  f"cost ${t.get('cost_usd', 0):.4f}" + (" (+ subscription runs)" if t.get("subscription_runs") else "")]
    lines += ["", "## Activity", *(f"- {k}: {n}" for k, n in kinds.most_common()), "",
              "## Project events", *(f"- {k}: {n}" for k, n in events.most_common(20)), "",
              f"## Errors ({len(errors)}, newest first)"]
    for r in errors[::-1][:60]:
        lines.append(f"- `{r.get('t')}` **{r.get('where') or r.get('type') or r.get('kind')}** {str(r.get('error') or r.get('note') or r.get('errors') or '')[:300]}")
    lines += ["", "## What to look at", "- Errors above: the element id and message show what failed; `trace` in the log has the code location.",
              "- `ai_run` records: tools the AI called, tokens, time; `ai_tool` with `error` = a tool the AI used wrongly.",
              "- `client_error`: errors in the interface (browser)."]
    return "\n".join(lines) + "\n"


def report_zip(project=None, usage=None) -> bytes:
    files, _ = _recent()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("report.md", summary_md(project, usage))
        for f in files:
            z.write(f, f"logs/{f.name}")
        if project is not None:
            z.writestr("recipe.json", json.dumps(project.recipe, ensure_ascii=False, indent=1))
            if project.last_validation:
                z.writestr("last_validation.json", json.dumps(project.last_validation, ensure_ascii=False, indent=1, default=str))
        if usage:
            z.writestr("ai_usage.json", json.dumps(usage, ensure_ascii=False, indent=1))
    return buf.getvalue()


__all__ = ["log", "log_exception", "report_zip", "summary_md", "LOG_DIR", "Path"]
