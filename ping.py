#!/usr/bin/env python3
"""One GLM API call per run; forward the model reply to Telegram.

Required env (GitHub Actions secrets):
  GLM_API_KEY            z.ai API key
  TELEGRAM_BOT_TOKEN     bot token from @BotFather
  TELEGRAM_CHAT_ID       target chat id

Optional env (defaults shown):
  GLM_ENDPOINT    https://api.z.ai/api/coding/paas/v4/chat/completions
  GLM_MODEL       glm-4.6
  GLM_PROMPT      short Persian connectivity prompt
  TELEGRAM_API_BASE  https://api.telegram.org  (debug/mock only)

Exits non-zero with a readable message on any failure; never prints secrets.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlsplit

DEFAULT_ENDPOINT = "https://api.z.ai/api/coding/paas/v4/chat/completions"
DEFAULT_MODEL = "glm-4.6"
DEFAULT_PROMPT = "یک سلام کوتاه فارسی بنویس و تأیید کن که اتصال AI برقرار است."
MAX_TOKENS = 50
TIMEOUT_GLM = 30
TIMEOUT_TG = 15

# Redact credential-shaped substrings before printing any API error body.
SECRET_PATTERNS = [
    re.compile(r"[A-Za-z0-9]{32}\.[A-Za-z0-9_-]{10,}"),  # z.ai style key
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}"),  # telegram bot token
]


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def require(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        fail(f"missing required secret/env: {name}")
    return val


def redact(text: str) -> str:
    for pat in SECRET_PATTERNS:
        text = pat.sub("***REDACTED***", text)
    return text[:500]


def http_json(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    host = urlsplit(url).netloc  # host only — never the URL (token lives in path)
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace") if e.fp else ""
        fail(f"HTTP {e.code} from {host}: {redact(body)}")
    except urllib.error.URLError as e:
        fail(f"cannot reach {host}: {e.reason}")
    except json.JSONDecodeError:
        fail(f"non-JSON response from {host}")


def ask_glm() -> str:
    payload = {
        "model": os.environ.get("GLM_MODEL", DEFAULT_MODEL),
        "max_tokens": MAX_TOKENS,
        "thinking": {"type": "disabled"},  # cuts reasoning length on the coding endpoint
        "messages": [
            {"role": "user", "content": os.environ.get("GLM_PROMPT", DEFAULT_PROMPT)}
        ],
    }
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {require('GLM_API_KEY')}",
    }
    url = os.environ.get("GLM_ENDPOINT", DEFAULT_ENDPOINT)
    data = http_json(url, payload, headers, TIMEOUT_GLM)
    try:
        text = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError, TypeError):
        fail(f"unexpected GLM response shape: {redact(json.dumps(data, ensure_ascii=False))}")
    if not text:
        fail("GLM returned empty content (possibly all tokens spent on reasoning)")
    return text


def send_telegram(text: str) -> None:
    base = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org").rstrip("/")
    url = f"{base}/bot{require('TELEGRAM_BOT_TOKEN')}/sendMessage"
    payload = {"chat_id": require("TELEGRAM_CHAT_ID"), "text": text}
    data = http_json(url, payload, {"content-type": "application/json"}, TIMEOUT_TG)
    if not data.get("ok"):
        fail(f"telegram refused: {redact(json.dumps(data, ensure_ascii=False))}")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    reply = ask_glm()
    send_telegram(f"🤖 GLM · {stamp}\n\n{reply}")
    print(f"sent OK · {stamp}\nmodel reply: {reply}")


if __name__ == "__main__":
    main()
