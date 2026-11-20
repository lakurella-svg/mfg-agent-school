"""Minimal local web UI for the MOC Assistant.

Standard library only: the page posts a question, the server runs the same
agent functions the CLI uses (run_offline / run_live / run_live_anthropic)
and streams each tool call, tool result and the final answer back as
newline-delimited JSON.

    python web/server.py                 # http://127.0.0.1:8101
    python web/server.py --port 8102     # another port

Live mode reads its settings from the environment of the process that
starts this server (LLM_PROVIDER, ANTHROPIC_API_KEY, LLM_BASE_URL,
LLM_API_KEY, LLM_MODEL, ...). Keys never reach the page.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT))

import moc_agent  # noqa: E402

INDEX_HTML = (Path(__file__).resolve().parent / "index.html").read_bytes()

# --- capture the agent's steps -------------------------------------------
# moc_agent's loops call the module-level run_tool() and trace(); wrapping
# them here gives the UI full tool results without changing the CLI.
_local = threading.local()
_orig_run_tool = moc_agent.run_tool
_orig_trace = moc_agent.trace
_run_lock = threading.Lock()  # one agent run at a time (shared stdout/trace)


def _emit(event: dict) -> None:
    sink = getattr(_local, "sink", None)
    if sink is not None:
        event.setdefault("ts", time.strftime("%H:%M:%S"))
        sink.put(event)


def _run_tool(name: str, args: dict) -> str:
    _emit({"type": "tool-call", "name": name, "args": args})
    result = _orig_run_tool(name, args)
    _emit({"type": "tool-result", "name": name, "result": result})
    return result


def _trace(step: str, detail: str) -> None:
    _orig_trace(step, detail)
    if step not in ("tool-call", "tool-result"):
        _emit({"type": "trace", "step": step, "detail": detail})


moc_agent.run_tool = _run_tool
moc_agent.trace = _trace


def live_status() -> dict:
    """What live mode would use, without ever exposing a secret."""
    if os.environ.get("LLM_PROVIDER") == "anthropic":
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LLM_API_KEY"))
        return {
            "available": has_key,
            "provider": "anthropic",
            "model": os.environ.get("LLM_MODEL", "claude-opus-5-5"),
            "reason": None if has_key else
            "LLM_PROVIDER=anthropic is set but ANTHROPIC_API_KEY is not.",
        }
    base, model = os.environ.get("LLM_BASE_URL"), os.environ.get("LLM_MODEL")
    if base and model:
        return {"available": True, "provider": "openai-compatible", "model": model,
                "endpoint": base, "reason": None}
    return {
        "available": False, "provider": None, "model": None,
        "reason": "Live mode is not configured. Set LLM_PROVIDER=anthropic and "
                  "ANTHROPIC_API_KEY, or LLM_BASE_URL, LLM_API_KEY and LLM_MODEL, "
                  "in the shell that starts the server, then restart it.",
    }


def _worker(question: str, mode: str, sink: queue.Queue) -> None:
    _local.sink = sink
    try:
        with _run_lock:
            if mode == "offline":
                answer = moc_agent.run_offline(question)
            elif os.environ.get("LLM_PROVIDER") == "anthropic":
                answer = moc_agent.run_live_anthropic(question)
            else:
                answer = moc_agent.run_live(question)
        sink.put({"type": "answer", "text": answer})
    except Exception as exc:  # surface model/endpoint errors on the page
        sink.put({"type": "error", "text": f"{type(exc).__name__}: {exc}"})
    finally:
        sink.put(None)
        _local.sink = None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"  # stream by writing until close

    def log_message(self, fmt, *args):  # quieter console
        sys.stderr.write(f"[web] {self.address_string()} {fmt % args}\n")

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(INDEX_HTML)))
            self.end_headers()
            self.wfile.write(INDEX_HTML)
        elif self.path == "/api/status":
            self._json(200, {"live": live_status()})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/ask":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "invalid JSON"})
        question = str(req.get("question", "")).strip()[:2000]
        mode = "live" if req.get("mode") == "live" else "offline"
        if not question:
            return self._json(400, {"error": "question is empty"})
        if mode == "live":
            status = live_status()
            if not status["available"]:
                return self._json(400, {"error": status["reason"]})

        sink: queue.Queue = queue.Queue()
        threading.Thread(target=_worker, args=(question, mode, sink), daemon=True).start()
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        while True:
            event = sink.get()
            if event is None:
                break
            try:
                self.wfile.write((json.dumps(event) + "\n").encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="MOC Assistant web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MOC_WEB_PORT", 8101)))
    args = parser.parse_args()

    moc_agent._enable_mlflow()  # no-op unless MLFLOW_TRACKING_URI is set
    try:
        server = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as exc:
        sys.exit(f"Cannot bind {args.host}:{args.port} ({exc}). Try --port <another>.")
    s = live_status()
    print(f"MOC Assistant web UI on http://{args.host}:{args.port}  "
          f"(live mode: {'on, ' + s['provider'] if s['available'] else 'off'}; Ctrl+C to stop)",
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
