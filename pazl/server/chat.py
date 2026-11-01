"""AI chat inside the app. Any AI drives the same tools as the MCP server (pazl.mcp.TOOLS):

- "anthropic"  Claude API (official SDK)
- OpenAI-compatible chat/completions: OpenAI, Google Gemini, DeepSeek, OpenRouter, Groq, Mistral, xAI,
  local Ollama / LM Studio, or any custom base URL
- "claude_code" the local Claude Code CLI (`claude -p`) with the pazl MCP server - works exactly like the terminal agent

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
import types
import typing
from pathlib import Path

import httpx

from ..paths import DATA, FROZEN

SETTINGS_FILE = DATA / "chat_settings.json"
MAX_STEPS = 60

PROVIDERS = {  # id: (title, base_url, needs key)
    "anthropic": ("Claude (Anthropic API)", "", True),
    "claude_code": ("Claude Code (локальный CLI, подписка)", "", False),
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

SYSTEM = (
    "You are the AI assistant built into 3dPazl, a constructor of watertight 3D buildings. The user talks to you in "
    "the app's chat panel and sees the model update live in the 3D viewport. Act through the tools - they are the same "
    "as the 3dPazl MCP server. Call `guide` once at the start of a conversation and follow it. Typical work: "
    "new_building / patch -> validate -> render_views (check every view, including sections and floor plans: floors, "
    "walls and textures inside the cuts must be clean) -> fix -> repeat. Use `note` for short progress messages. "
    "Reply in the user's language, briefly: what you did and what you checked."
)


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
            "claude_cli": bool(shutil.which("claude"))}


# ------------------------------------------------------------------ session
class Chat:
    def __init__(self, broadcast):
        self.broadcast = broadcast
        self.settings = load_settings()
        self.transcript: list[dict] = []   # what the chat panel shows
        self.history: list = []            # provider-specific conversation
        self.history_provider = None
        self.cli_session = None
        self.busy = False
        self.stop_flag = False
        self.proc = None

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

    def send(self, text: str):
        if self.busy:
            raise RuntimeError("ИИ ещё отвечает")
        if not text.strip():
            raise ValueError("пустое сообщение")
        self.busy, self.stop_flag = True, False
        self._emit("user", text)
        threading.Thread(target=self._run, args=(text,), daemon=True).start()

    # -------------------------------------------------- internals
    def _emit(self, role, text, **extra):
        item = {"role": role, "text": text, **extra}
        self.transcript.append(item)
        self.broadcast({"type": "chat", **item})

    def _run(self, text):
        p = self.settings.get("provider", "anthropic")
        if self.history_provider != p:  # switching AI starts a fresh conversation (formats differ)
            self.history, self.cli_session, self.history_provider = [], None, p
        try:
            if p == "anthropic":
                self._anthropic(text)
            elif p == "claude_code":
                self._claude_code(text)
            else:
                self._openai_compat(p, text)
        except Exception as ex:
            self._emit("error", f"{type(ex).__name__}: {ex}")
        finally:
            self.busy = False
            self.broadcast({"type": "chat", "role": "done", "text": ""})

    def _agent(self, p):
        return "chat:" + p

    def _tool_call(self, p, name, args):
        self._emit("tool", name, args=args)
        res, imgs = run_tool(name, args or {}, self._agent(p))
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
        self.history.append({"role": "user", "content": text})
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
        self.history.append({"role": "user", "content": text})
        vision = s.get("vision", True)
        for _ in range(MAX_STEPS):
            if self.stop_flag:
                return self._emit("info", "остановлено")
            r = httpx.post(f"{base}/chat/completions", headers=headers, timeout=600,
                           json={"model": model, "messages": self.history, "tools": tools})
            if r.status_code >= 400:
                return self._emit("error", f"{PROVIDERS[p][0]} {r.status_code}: {r.text[:500]}")
            msg = r.json()["choices"][0]["message"]
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

    # ---- local Claude Code CLI with the pazl MCP server
    def _claude_code(self, text):
        exe = shutil.which("claude")
        if not exe:
            return self._emit("error", "Claude Code не найден. Установите его (claude.com/claude-code) и войдите: `claude`.")
        cmd_mcp = [sys.executable, "--mcp"] if FROZEN else [sys.executable, "-m", "pazl.mcp"]
        cfg = {"mcpServers": {"pazl": {"command": cmd_mcp[0], "args": cmd_mcp[1:],
                                       "env": {"PAZL_AGENT": self._agent("claude_code")}}}}
        cfg_path = Path(tempfile.gettempdir()) / "pazl_chat_mcp.json"
        cfg_path.write_text(json.dumps(cfg), "utf-8")
        args = [exe, "-p", text, "--output-format", "stream-json", "--verbose", "--mcp-config", str(cfg_path),
                "--strict-mcp-config", "--allowedTools", "mcp__pazl", "--append-system-prompt", SYSTEM]
        model = self.settings.get("models", {}).get("claude_code")
        if model:
            args += ["--model", model]
        if self.cli_session:
            args += ["--resume", self.cli_session]
        flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
        self.proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(DATA),
                                     text=True, encoding="utf-8", errors="replace", creationflags=flags)
        failed = False
        for line in self.proc.stdout:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("session_id"):
                self.cli_session = ev["session_id"]
            if ev.get("type") == "assistant" and not ev.get("error"):
                for b in ev.get("message", {}).get("content", []):
                    if b.get("type") == "text" and b.get("text", "").strip():
                        self._emit("assistant", b["text"])
                    elif b.get("type") == "tool_use":
                        self._emit("tool", b.get("name", "").removeprefix("mcp__pazl__"), args=b.get("input"))
            elif ev.get("type") == "result" and ev.get("is_error"):
                msg = str(ev.get("result") or ev.get("subtype"))
                if "authenticate" in msg or "login" in msg.lower():
                    msg += " - откройте терминал и выполните `claude`, чтобы войти заново."
                self._emit("error", msg)
                failed = True
        self.proc.wait()
        if self.proc.returncode and not self.stop_flag and not failed:
            err = self.proc.stderr.read().strip()
            self._emit("error", f"claude завершился с кодом {self.proc.returncode}: {err[:500]}")
        if self.stop_flag:
            self._emit("info", "остановлено")
