"""AI chat inside the app. Any AI drives the same tools as the MCP server (pazl.mcp.TOOLS):

- "anthropic"  Claude API (official SDK)
- OpenAI-compatible chat/completions: OpenAI, Google Gemini, DeepSeek, OpenRouter, Groq, Mistral, xAI,
  local Ollama / LM Studio, or any custom base URL
- AI apps signed in with the user's own account (subscription, no API key), like the VS Code extensions:
  Claude Code, OpenAI Codex (ChatGPT account), Gemini CLI (Google account) - run headless with the pazl MCP server

Settings (incl. API keys) live in <DATA>/chat_settings.json on this computer only; keys are never sent to the browser.
"""
from __future__ import annotations

import base64
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import typing
from pathlib import Path

import httpx

from ..paths import DATA, FROZEN
from .logs import log, log_exception

SETTINGS_FILE = DATA / "chat_settings.json"
MAX_STEPS = 60

PROVIDERS = {  # id: (title, base_url, needs key)
    "anthropic": ("Claude (Anthropic API)", "", True),
    "claude_code": ("Claude Code — вход аккаунтом Claude", "", False),
    "codex": ("ChatGPT / Codex — вход аккаунтом OpenAI", "", False),
    "gemini_cli": ("Gemini CLI — вход аккаунтом Google", "", False),
    "openai": ("OpenAI", "https://api.openai.com/v1", True),
    "gemini": ("Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai", True),
    "deepseek": ("DeepSeek", "https://api.deepseek.com/v1", True),
    "openrouter": ("OpenRouter (любые модели)", "https://openrouter.ai/api/v1", True),
    "groq": ("Groq", "https://api.groq.com/openai/v1", True),
    "mistral": ("Mistral", "https://api.mistral.ai/v1", True),
    "xai": ("xAI Grok", "https://api.x.ai/v1", True),
    "ollama": ("Ollama (локально)", "http://localhost:11434/v1", False),
    "lmstudio": ("LM Studio (локально)", "http://localhost:1234/v1", False),
    "custom": ("Свой OpenAI-совместимый URL", "", False),
}
DEFAULT_MODEL = {"anthropic": "claude-opus-5-5"}
FALLBACK_MODELS = ("claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5")
# USD per 1M tokens: input, output (cache reads ~0.1x input, cache writes 1.25x input) - Claude API list prices
PRICES = {"claude-fable-5-1": (10.0, 50.0), "claude-fable-5": (10.0, 50.0), "claude-opus-5-5": (4.0, 20.0), "claude-opus-5": (5.0, 25.0),
          "claude-opus-4-8": (5.0, 25.0), "claude-opus-4-7": (5.0, 25.0), "claude-opus-4-6": (5.0, 25.0),
          "claude-sonnet-5-5": (2.0, 10.0), "claude-sonnet-5": (2.0, 10.0), "claude-sonnet-4-6": (3.0, 15.0),
          "claude-haiku-5-5": (0.10, 0.50), "claude-haiku-4-5": (1.0, 5.0)}


def price_of(model, inp, out, cache_read=0, cache_write=0):
    pr = PRICES.get(model)
    if not pr:
        return None
    return (inp * pr[0] + out * pr[1] + cache_read * pr[0] * 0.1 + cache_write * pr[0] * 1.25) / 1e6

SYSTEM = (
    "You are the AI assistant built into 3dPazl, a constructor of watertight 3D buildings. The user talks to you in "
    "the app's chat panel and sees the model update live in the 3D viewport. Act through the tools - they are the same "
    "as the 3dPazl MCP server. If you have not read `guide` in this conversation, read it first, then carry out the user's "
    "request in the same turn - never stop after reading the guide or ask what to build when the request already says it. "
    "Typical work: "
    "new_building / patch -> validate -> render_views (check every view, including sections and floor plans: floors, "
    "walls and textures inside the cuts must be clean) -> fix -> repeat. Use `note` for short progress messages. "
    "Reply in the user's language, briefly: what you did and what you checked."
)


def usage_total(runs):
    t = {"runs": len(runs), "input": 0, "output": 0, "cache_read": 0, "cost_usd": 0.0, "subscription_runs": 0, "by_provider": {}}
    for r in runs:
        t["input"] += r.get("input", 0); t["output"] += r.get("output", 0); t["cache_read"] += r.get("cache_read", 0)
        bp = t["by_provider"].setdefault(r.get("provider", "?"), {"runs": 0, "input": 0, "output": 0, "cost_usd": 0.0})
        bp["runs"] += 1; bp["input"] += r.get("input", 0); bp["output"] += r.get("output", 0)
        if r.get("cost_usd") is not None and "подписке" not in (r.get("note") or ""):
            t["cost_usd"] += r["cost_usd"]; bp["cost_usd"] += r["cost_usd"]
        elif "подписке" in (r.get("note") or "") or "аккаунту" in (r.get("note") or ""):
            t["subscription_runs"] += 1
    t["cost_usd"] = round(t["cost_usd"], 6)
    return t


# ------------------------------------------------------------------ tools
def _tools() -> dict:
    from .. import mcp as M
    return M.TOOLS


_PY2JSON = {str: "string", int: "integer", float: "number", bool: "boolean", dict: "object", list: "array"}
_ITEMS = {"views": {"type": "string"}, "target": {"type": "number"}}


def _schema(name: str, fn) -> dict:
    hints = typing.get_type_hints(fn)
    props, req = {}, []
    for pname, prm in inspect.signature(fn).parameters.items():
        t = hints.get(pname, str)
        args = [a for a in typing.get_args(t) if a is not type(None)] if isinstance(t, types.UnionType) or typing.get_origin(t) is typing.Union else [t]
        if str in args and dict in args:  # e.g. windows: dict | str -> JSON string or a word
            sch = {"type": "string", "description": "JSON object or a keyword"}
        else:
            sch = {"type": _PY2JSON.get(args[0], "string")}
        if sch["type"] == "array":
            sch["items"] = _ITEMS.get(pname, {"type": "object"})
        if prm.default is inspect.Parameter.empty:
            req.append(pname)
        elif prm.default is not None:
            sch["description"] = f"default {json.dumps(prm.default, ensure_ascii=False)}"
        props[pname] = sch
    return {"name": name, "description": (fn.__doc__ or name).strip(), "parameters":
            {"type": "object", "properties": props, "required": req}}


def run_tool(name: str, args: dict, agent: str) -> tuple[str, list[bytes]]:
    """-> (text result, png images)."""
    from .. import mcp as M
    fn = _tools().get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool {name}"}), []
    if isinstance(args.get("windows"), str) and args["windows"].strip().startswith("{"):
        args["windows"] = json.loads(args["windows"])
    M.AGENT = agent
    try:
        out = fn(**args)
    except Exception as ex:
        return json.dumps({"error": f"{type(ex).__name__}: {ex}"}, ensure_ascii=False), []
    texts, images = [], []
    for x in out if isinstance(out, list) else [out]:
        if isinstance(x, str):
            texts.append(x)
        elif getattr(x, "path", None):
            images.append(Path(x.path).read_bytes())
        elif getattr(x, "data", None):
            images.append(x.data)
        else:
            texts.append(json.dumps(x, ensure_ascii=False, default=str))
    return "\n".join(texts) or "ok", images


# ------------------------------------------------------------------ settings
def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text("utf-8"))
    except Exception:
        return {"provider": "anthropic", "keys": {}, "models": {}, "base_urls": {}, "effort": "high", "vision": True}


def public_settings(s: dict) -> dict:
    keys = s.get("keys", {})
    return {"provider": s.get("provider", "anthropic"), "models": s.get("models", {}), "base_urls": s.get("base_urls", {}),
            "effort": s.get("effort", "high"), "vision": s.get("vision", True),
            "has_key": {p: bool(k) for p, k in keys.items()},
            "providers": [{"id": k, "title": v[0], "base_url": v[1], "needs_key": v[2], "model": DEFAULT_MODEL.get(k, "")}
                          for k, v in PROVIDERS.items()],
            "cli": {p: bool(shutil.which(c["exe"])) for p, c in CLIS.items()}}


# ------------------------------------------------------------------ session
class Chat:
    def __init__(self, broadcast, project=None, cid="1"):
        self.cid = cid                     # several chats (different AIs) can work at the same time
        self.broadcast = broadcast
        self.project = project
        self.settings = load_settings()
        self.transcript: list[dict] = []   # what the chat panel shows
        self.history: list = []            # provider-specific conversation
        self.history_provider = None
        self.cli_session = None
        self.busy = False
        self.stop_flag = False
        self.proc = None
        self.image = None
        self.run = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0, "cost": None, "note": "", "tools": [], "t0": 0, "request": ""}

    # -------------------------------------------------- api
    def save_settings(self, upd: dict):
        s = self.settings
        if upd.get("provider") in PROVIDERS:
            s["provider"] = upd["provider"]
        p = s.get("provider", "anthropic")
        for k in ("effort", "vision"):
            if k in upd:
                s[k] = upd[k]
        if "model" in upd:
            s.setdefault("models", {})[p] = str(upd["model"]).strip()
        if "base_url" in upd:
            s.setdefault("base_urls", {})[p] = str(upd["base_url"]).strip()
        if upd.get("api_key") is not None:  # "" clears the key
            s.setdefault("keys", {})[p] = str(upd["api_key"]).strip()
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=1), "utf-8")
        return public_settings(s)

    def state(self):
        return {"transcript": self.transcript[-300:], "busy": self.busy, "settings": public_settings(self.settings)}

    def reset(self):
        if self.busy:
            raise RuntimeError("подождите окончания ответа или нажмите «Стоп»")
        self.transcript, self.history, self.cli_session = [], [], None

    def stop(self):
        self.stop_flag = True
        if self.proc and self.proc.poll() is None:
            self.proc.kill()

    def send(self, text: str, scope: list | None = None, image: str | None = None):
        """scope: element ids the AI may change (marks on the model); image: data-URL screenshot with the marks."""
        if self.busy:
            raise RuntimeError("ИИ ещё отвечает")
        if not text.strip():
            raise ValueError("пустое сообщение")
        self.busy, self.stop_flag = True, False
        self.run = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0, "cost": None, "note": "", "tools": [], "t0": time.time(),
                    "request": text[:300]}
        self.image = None
        if image and image.startswith("data:image/png;base64,") and self.project is not None:
            d = self.project.dir / "renders"
            d.mkdir(parents=True, exist_ok=True)
            self.image = d / f"marks_{len(list(d.glob('marks_*.png'))) + 1:03d}.png"
            self.image.write_bytes(base64.b64decode(image.split(",", 1)[1]))
        if self.project is not None:
            self.project.scope = {str(s) for s in scope if s} if scope else None
        self._emit("user", text, scope=sorted(scope or []))
        threading.Thread(target=self._run, args=(text,), daemon=True).start()

    # -------------------------------------------------- internals
    def _emit(self, role, text, **extra):
        item = {"role": role, "text": text, **extra}
        self.transcript.append(item)
        self.broadcast({"type": "chat", "chat": self.cid, **item})

    def _use(self, inp=0, out=0, cache_read=0, cache_write=0, cost=None, note=""):
        r = self.run
        r["in"] += int(inp or 0); r["out"] += int(out or 0)
        r["cache_read"] += int(cache_read or 0); r["cache_write"] += int(cache_write or 0)
        if cost is not None:
            r["cost"] = (r["cost"] or 0.0) + float(cost)
        if note:
            r["note"] = note

    def _finish_usage(self, p):
        """One AI run: tokens, money, tools, time -> project usage.json, the chat and the log."""
        r = self.run
        model = self.settings.get("models", {}).get(p) or DEFAULT_MODEL.get(p, "")
        rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "provider": p, "model": model, "input": r["in"], "output": r["out"],
               "cache_read": r["cache_read"], "cache_write": r["cache_write"],
               "cost_usd": round(r["cost"], 6) if r["cost"] is not None else None, "note": r["note"],
               "tools": r["tools"], "seconds": round(time.time() - r["t0"], 1), "request": r["request"]}
        log("ai_run", **rec)
        if self.project is not None:
            f = self.project.dir / "usage.json"
            try:
                data = json.loads(f.read_text("utf-8"))
            except (OSError, ValueError):
                data = {"runs": []}
            data["runs"].append(rec)
            data["total"] = usage_total(data["runs"])
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
        cost = f"${rec['cost_usd']:.4f}" if rec["cost_usd"] is not None else (rec["note"] or "цена неизвестна")
        self._emit("usage", f"токены: {rec['input']:,} → {rec['output']:,}" + (f" (+кэш {rec['cache_read']:,})" if rec["cache_read"] else "")
                   + f" · {cost} · {len(rec['tools'])} инстр. · {rec['seconds']} с", usage=rec)

    def _run(self, text):
        p = self.settings.get("provider", "anthropic")
        if self.history_provider != p:  # switching AI starts a fresh conversation (formats differ)
            self.history, self.cli_session, self.history_provider = [], None, p
        try:
            if p == "anthropic":
                self._anthropic(text)
            elif p in CLIS:
                self._cli(p, text)
            else:
                self._openai_compat(p, text)
        except Exception as ex:
            log_exception("chat", ex, provider=p)
            self._emit("error", f"{type(ex).__name__}: {ex}")
        finally:
            if self.project is not None:
                self.project.scope = None
            try:
                self._finish_usage(p)
            except Exception as ex:  # usage must not break the chat
                log_exception("usage", ex)
            self.busy = False
            self.broadcast({"type": "chat", "chat": self.cid, "role": "done", "text": ""})

    def _agent(self, p):
        return "chat:" + p + ("" if self.cid == "1" else "#" + self.cid)

    def _tool_call(self, p, name, args):
        self._emit("tool", name, args=args)
        self.run["tools"].append(name)
        res, imgs = run_tool(name, args or {}, self._agent(p))
        err = res if res.startswith('{"error"') else None
        log("ai_tool", provider=p, tool=name, args=args, error=err)
        return res, imgs

    # ---- Claude API
    def _anthropic(self, text):
        import anthropic
        key = self.settings.get("keys", {}).get("anthropic") or None
        client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
        model = self.settings.get("models", {}).get("anthropic") or DEFAULT_MODEL["anthropic"]
        tools = [{"name": d["name"], "description": d["description"], "input_schema": d["parameters"]}
                 for d in (_schema(n, f) for n, f in _tools().items())]
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"} if model in FALLBACK_MODELS else {}
        content = [{"type": "text", "text": text}]
        if self.image:
            content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                            "data": base64.b64encode(self.image.read_bytes()).decode()}})
        self.history.append({"role": "user", "content": content})
        for _ in range(MAX_STEPS):
            if self.stop_flag:
                return self._emit("info", "остановлено")
            try:
                r = client.beta.messages.create(
                    model=model, max_tokens=16000, system=SYSTEM, tools=tools, messages=self.history,
                    output_config={"effort": self.settings.get("effort", "high")},
                    cache_control={"type": "ephemeral"}, **extra)
            except anthropic.AuthenticationError:
                self.history.pop()
                return self._emit("error", "Неверный API-ключ Anthropic (настройки чата).")
            except TypeError as ex:  # no key anywhere (settings, ANTHROPIC_API_KEY, `ant auth login` profile)
                if "authentication" not in str(ex):
                    raise
                self.history.pop()
                return self._emit("error", "Укажите API-ключ Anthropic в настройках чата (или выберите Claude Code).")
            except anthropic.RateLimitError:
                return self._emit("error", "Лимит запросов Anthropic, попробуйте позже.")
            except anthropic.APIStatusError as ex:
                return self._emit("error", f"Anthropic API {ex.status_code}: {ex.message}")
            except anthropic.APIConnectionError:
                return self._emit("error", "Нет связи с api.anthropic.com.")
            self.history.append({"role": "assistant", "content": r.content})
            u = r.usage
            ci, cw = getattr(u, "cache_read_input_tokens", 0) or 0, getattr(u, "cache_creation_input_tokens", 0) or 0
            self._use(u.input_tokens, u.output_tokens, ci, cw, price_of(r.model or model, u.input_tokens, u.output_tokens, ci, cw))
            for b in r.content:
                if b.type == "text" and b.text.strip():
                    self._emit("assistant", b.text)
            if r.stop_reason == "refusal":
                return self._emit("error", "Модель отказалась выполнять запрос.")
            if r.stop_reason == "max_tokens":
                return self._emit("error", "Ответ обрезан по длине.")
            if r.stop_reason == "pause_turn":
                continue
            calls = [b for b in r.content if b.type == "tool_use"]
            if r.stop_reason != "tool_use" or not calls:
                return
            results = []
            for c in calls:
                res, imgs = self._tool_call("anthropic", c.name, dict(c.input or {}))
                content = [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                         "data": base64.b64encode(i).decode()}} for i in imgs]
                content.append({"type": "text", "text": res[:60000]})
                results.append({"type": "tool_result", "tool_use_id": c.id, "content": content})
            self.history.append({"role": "user", "content": results})
        self._emit("error", f"Остановлено после {MAX_STEPS} шагов.")

    # ---- OpenAI-compatible chat/completions (OpenAI, Gemini, DeepSeek, OpenRouter, Ollama, ...)
    def _openai_compat(self, p, text):
        s = self.settings
        base = (s.get("base_urls", {}).get(p) or PROVIDERS[p][1]).rstrip("/")
        model = s.get("models", {}).get(p)
        if not base:
            return self._emit("error", "Укажите адрес (base URL) в настройках чата.")
        if not model:
            return self._emit("error", "Укажите модель в настройках чата.")
        key = s.get("keys", {}).get(p, "")
        if PROVIDERS[p][2] and not key:
            return self._emit("error", f"Укажите API-ключ для {PROVIDERS[p][0]} в настройках чата.")
        headers = {"Authorization": f"Bearer {key or 'none'}"}
        tools = [{"type": "function", "function": _schema(n, f)} for n, f in _tools().items()]
        if not self.history:
            self.history.append({"role": "system", "content": SYSTEM})
        vision = s.get("vision", True)
        if self.image and vision:
            url = "data:image/png;base64," + base64.b64encode(self.image.read_bytes()).decode()
            self.history.append({"role": "user", "content": [{"type": "text", "text": text},
                                                             {"type": "image_url", "image_url": {"url": url}}]})
        else:
            self.history.append({"role": "user", "content": text})
        for _ in range(MAX_STEPS):
            if self.stop_flag:
                return self._emit("info", "остановлено")
            r = httpx.post(f"{base}/chat/completions", headers=headers, timeout=600,
                           json={"model": model, "messages": self.history, "tools": tools})
            if r.status_code >= 400:
                return self._emit("error", f"{PROVIDERS[p][0]} {r.status_code}: {r.text[:500]}")
            body = r.json()
            u = body.get("usage") or {}
            self._use(u.get("prompt_tokens", 0), u.get("completion_tokens", 0), note="цена у провайдера")
            msg = body["choices"][0]["message"]
            msg = {k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")}
            self.history.append(msg)
            if msg.get("content"):
                self._emit("assistant", msg["content"] if isinstance(msg["content"], str) else json.dumps(msg["content"]))
            calls = msg.get("tool_calls") or []
            if not calls:
                return
            pics = []
            for c in calls:
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args, res = None, '{"error": "arguments are not valid JSON"}'
                if args is not None:
                    res, imgs = self._tool_call(p, c["function"]["name"], args)
                    pics += imgs
                self.history.append({"role": "tool", "tool_call_id": c["id"], "content": res[:60000]})
            if pics and vision:  # tool messages carry text only -> pictures go in a user message
                self.history.append({"role": "user", "content": [{"type": "text", "text": "Rendered views:"}] + [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(i).decode()}}
                    for i in pics]})
        self._emit("error", f"Остановлено после {MAX_STEPS} шагов.")


    # ---- AI apps signed in with the user's account (like the VS Code extensions): Claude Code, Codex, Gemini CLI.
    # Each runs headless with the pazl MCP server attached; the conversation continues via its session id.
    def _mcp_cmd(self, p):
        cmd = [sys.executable, "--mcp"] if FROZEN else [sys.executable, "-m", "pazl.mcp"]
        return cmd[0], cmd[1:], {"PAZL_AGENT": self._agent(p)}

    def _first(self, text):  # CLIs without a system-prompt flag get the instructions with the first message
        return text if self.cli_session else f"USER REQUEST (do it now, in this turn):\n{text}\n\n---\nHow to work:\n{SYSTEM}"

    def _cli_args(self, p, exe, text):
        model = self.settings.get("models", {}).get(p)
        cmd, cargs, env = self._mcp_cmd(p)
        if p == "claude_code":
            cfg = Path(tempfile.gettempdir()) / "pazl_chat_mcp.json"
            cfg.write_text(json.dumps({"mcpServers": {"pazl": {"command": cmd, "args": cargs, "env": env}}}), "utf-8")
            if self.image:
                text += f"\n\nScreenshot with the marks (red numbers/lines): {self.image} - look at it with Read."
            args = [exe, "-p", text, "--output-format", "stream-json", "--verbose", "--mcp-config", str(cfg),
                    "--strict-mcp-config", "--allowedTools", "mcp__pazl,Read" if self.image else "mcp__pazl",
                    "--append-system-prompt", SYSTEM]
            args += ["--model", model] if model else []
            args += ["--resume", self.cli_session] if self.cli_session else []
            return args, DATA
        if p == "codex":
            def toml(v):  # JSON strings/arrays are valid TOML values
                return json.dumps(v, ensure_ascii=False)
            args = [exe, "exec", "--json", "--skip-git-repo-check", "-s", "read-only",
                    "-c", f"mcp_servers.pazl.command={toml(cmd)}", "-c", f"mcp_servers.pazl.args={toml(cargs)}",
                    "-c", "mcp_servers.pazl.env={PAZL_AGENT=" + toml(env["PAZL_AGENT"]) + "}",
                    "-c", 'approval_policy="never"',
                    # with approvals off Codex declines MCP calls unless the server's tools are pre-approved
                    "-c", 'mcp_servers.pazl.default_tools_approval_mode="approve"']
            args += ["-m", model] if model else []
            args += ["-i", str(self.image)] if self.image else []
            args += ["resume", self.cli_session] if self.cli_session else []
            self.stdin_text = self._first(text)  # via stdin: codex.cmd (npm shim) would cut a multi-line argument
            return args + ["-"], DATA
        # gemini_cli: MCP servers come from the workspace's .gemini/settings.json
        ws = DATA / "ai_workspace" / "gemini"
        (ws / ".gemini").mkdir(parents=True, exist_ok=True)
        (ws / ".gemini" / "settings.json").write_text(json.dumps(
            {"mcpServers": {"pazl": {"command": cmd, "args": cargs, "env": env, "trust": True}}}), "utf-8")
        if self.image:
            text += f"\n\nScreenshot with the marks (red numbers/lines): @{self.image}"
        self.stdin_text = self._first(text)  # via stdin (+ an empty -p): gemini.cmd would cut a multi-line argument
        args = [exe, "-p", " ", "-o", "stream-json", "--approval-mode", "yolo",
                "--allowed-mcp-server-names", "pazl", "--skip-trust"]
        args += ["-m", model] if model else []
        args += ["--resume", "latest"] if self.cli_session else []  # the workspace holds only this chat
        return args, ws

    def _cli(self, p, text):
        exe = shutil.which(CLIS[p]["exe"])
        if not exe:
            return self._emit("error", f"{PROVIDERS[p][0]}: программа не установлена - нажмите «Установить».")
        self.stdin_text = None
        args, cwd = self._cli_args(p, exe, text)
        had_session = self.cli_session
        flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
        err = tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE if self.stdin_text else subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=err, cwd=str(cwd), text=True, encoding="utf-8", errors="replace", creationflags=flags,
                                     env=_cli_env())
        if self.stdin_text:
            self.proc.stdin.write(self.stdin_text)
            self.proc.stdin.close()
        st = {"failed": False, "buf": ""}
        for line in self.proc.stdout:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            getattr(self, "_ev_" + p)(p, ev, st)
        self.proc.wait()
        if st["buf"].strip():
            self._emit("assistant", st["buf"])
        if self.stop_flag:
            return self._emit("info", "остановлено")
        if self.proc.returncode and not st["failed"]:
            err.seek(0)
            self._fail(p, st, f"{CLIS[p]['exe']} завершился с кодом {self.proc.returncode}: {err.read().strip()[-500:]}")
        if st["failed"] and not had_session:  # nothing to resume: the next message starts the conversation again
            self.cli_session = None

    def _fail(self, p, st, msg):
        st["failed"] = True
        if any(w in msg.lower() for w in ("auth", "login", "401", "unauthorized", "sign in")):
            msg += "  →  нажмите «Войти», чтобы войти в аккаунт."
        self._emit("error", msg)

    def _ev_claude_code(self, p, ev, st):
        if ev.get("session_id"):
            self.cli_session = ev["session_id"]
        if ev.get("type") == "assistant" and not ev.get("error"):
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "text" and b.get("text", "").strip():
                    self._emit("assistant", b["text"])
                elif b.get("type") == "tool_use" and b.get("name", "").startswith("mcp__pazl__"):  # not CLI internals
                    self._emit("tool", b["name"].removeprefix("mcp__pazl__"), args=b.get("input"))
                    self.run["tools"].append(b["name"].removeprefix("mcp__pazl__"))
        if ev.get("type") == "result":  # tokens + API-equivalent cost of the run (subscription: not billed per token)
            u = ev.get("usage") or {}
            self._use(u.get("input_tokens", 0), u.get("output_tokens", 0), u.get("cache_read_input_tokens", 0),
                      u.get("cache_creation_input_tokens", 0), ev.get("total_cost_usd"), "по подписке Claude (≈ цена API)")
        if ev.get("type") == "result" and ev.get("is_error"):
            self._fail(p, st, str(ev.get("result") or ev.get("subtype")))

    def _ev_codex(self, p, ev, st):
        t, item = ev.get("type"), ev.get("item") or {}
        if t == "thread.started":
            self.cli_session = ev.get("thread_id")
        elif t == "item.started" and item.get("type") == "mcp_tool_call":
            self._emit("tool", item.get("tool", ""), args=item.get("arguments"))
            self.run["tools"].append(item.get("tool", ""))
        elif t == "turn.completed":
            u = ev.get("usage") or {}
            self._use(u.get("input_tokens", 0), u.get("output_tokens", 0), u.get("cached_input_tokens", 0), note="по подписке ChatGPT")
        elif t == "item.completed" and item.get("type") == "agent_message" and item.get("text", "").strip():
            self._emit("assistant", item["text"])
        elif t == "turn.failed":
            self._fail(p, st, str((ev.get("error") or {}).get("message", "ошибка")))
        elif t == "error" and not str(ev.get("message", "")).startswith("Reconnecting"):
            self._fail(p, st, str(ev.get("message")))

    def _ev_gemini_cli(self, p, ev, st):
        t = ev.get("type")
        if t == "init":
            self.cli_session = ev.get("session_id") or "1"
        elif t == "message" and ev.get("role") == "assistant":
            st["buf"] += ev.get("content", "") if ev.get("delta") else "\n" + ev.get("content", "")
        elif t == "tool_use":
            if st["buf"].strip():
                self._emit("assistant", st["buf"])
            st["buf"] = ""
            self._emit("tool", str(ev.get("tool_name", "")).removeprefix("mcp_pazl_"), args=ev.get("parameters"))
        if t == "result":
            s = ev.get("stats") or {}
            self._use(s.get("input_tokens", 0), s.get("output_tokens", 0), s.get("cached", 0), note="по аккаунту Google")
        if t == "result" and ev.get("status") not in (None, "success"):
            self._fail(p, st, json.dumps(ev.get("error") or ev, ensure_ascii=False)[:500])
        elif t == "error":
            self._fail(p, st, str(ev.get("message") or ev)[:500])

    # ---- account sign-in / install, in a visible console window (the CLI opens the browser itself)
    def account(self, p):
        c = CLIS.get(p)
        if not c:
            return {"cli": False}
        exe = shutil.which(c["exe"])
        out = {"cli": True, "installed": bool(exe), "status": ""}
        if exe and c["status"]:
            try:
                r = subprocess.run([exe, *c["status"]], capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   timeout=20, stdin=subprocess.DEVNULL, creationflags=0x08000000 if os.name == "nt" else 0,
                                   env=_cli_env())
                out["status"] = (r.stdout + r.stderr).strip()[-300:]
                try:  # claude auth status prints JSON {"loggedIn": ...}
                    out["logged_in"] = bool(json.loads(r.stdout)["loggedIn"])
                except (ValueError, KeyError, TypeError):
                    out["logged_in"] = r.returncode == 0 and "not logged" not in out["status"].lower()
            except Exception as ex:
                out["status"] = str(ex)
        return out

    def open_console(self, p, what):
        c = CLIS[p]
        if what == "install":
            cmd = ["npm", "install", "-g", c["npm"]]
        else:
            exe = shutil.which(c["exe"])
            if not exe:
                raise RuntimeError("сначала установите программу")
            cmd = [exe, *c["login"]]
        if os.name == "nt":
            subprocess.Popen(["cmd", "/k", *cmd], env=_cli_env(), creationflags=0x00000010)  # CREATE_NEW_CONSOLE
        else:
            subprocess.Popen(cmd, env=_cli_env())
        return {"ok": True}


def _cli_env() -> dict:
    """Environment for the AI apps: without the variables of an AI session that may have started 3dPazl
    (CLAUDECODE, CLAUDE_CODE_*, ANTHROPIC_BASE_URL, ...). With them `claude` acts as a nested session and ignores
    the user's own sign-in; an ANTHROPIC_API_KEY would also override the subscription."""
    return {k: v for k, v in os.environ.items() if not k.upper().startswith(("CLAUDE", "ANTHROPIC_"))}


CLIS = {  # account-based AI apps: executable, npm package, sign-in and status commands
    "claude_code": {"exe": "claude", "npm": "@anthropic-ai/claude-code", "login": ["auth", "login"], "status": ["auth", "status"]},
    "codex": {"exe": "codex", "npm": "@openai/codex", "login": ["login"], "status": ["login", "status"]},
    "gemini_cli": {"exe": "gemini", "npm": "@google/gemini-cli", "login": [], "status": None},  # signs in on its own screen
}
