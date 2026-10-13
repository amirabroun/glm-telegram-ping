# glm-telegram-ping

Minimal GitHub Actions project: every 5 minutes, send one tiny request to the
GLM API (Z.ai) and forward the model's actual reply to a Telegram chat.
Purpose: verify the real wiring between GitHub Actions → GLM API → Telegram
Bot API. Nothing else.

## How it works

- `.github/workflows/glm-telegram.yml` — `workflow_dispatch` (manual run from
  the Actions tab) + schedule `2-59/5 * * * *` (every 5 min, offset 2).
- `ping.py` — one GLM request (`max_tokens: 50`, thinking disabled), then one
  Telegram `sendMessage` with the model reply prefixed by
  `🤖 GLM · <UTC timestamp>`. Python stdlib only. Any failure exits non-zero,
  so the workflow shows red. Secrets are never printed.

## Required repository secrets (Settings → Secrets and variables → Actions)

| Secret              | Value                                  |
|---------------------|----------------------------------------|
| `GLM_API_KEY`       | Z.ai API key (same key used for GLM access) |
| `TELEGRAM_BOT_TOKEN`| Bot token from @BotFather              |
| `TELEGRAM_CHAT_ID`  | Numeric chat id that receives messages |

## Configuration (optional)

Defaults live in `ping.py` and can be overridden via the `env:` block of the
workflow:

- `GLM_ENDPOINT` — default `https://api.z.ai/api/coding/paas/v4/chat/completions`
  (the GLM Coding Plan endpoint). Alternative: `https://api.z.ai/api/anthropic/v1/messages`
  — note: on that endpoint the `thinking: disabled` flag is ignored and
  reasoning consumes the token budget, so short replies get truncated.
- `GLM_MODEL` — default `glm-4.6`.
- `GLM_PROMPT` — default short Persian connectivity prompt.

## Manual run / logs

Actions tab → **glm-telegram-ping** → **Run workflow**. Watch the run and open
its log for the sent reply and any error (`ERROR: HTTP … from api.z.ai` etc.).

## Caveats

- Scheduled runs fire only from the default branch, may start minutes late at
  busy hours, and GitHub disables schedules after 60 days of repo inactivity.
- On a **private** repo, 288 runs/day eats the free 2,000 Actions minutes/month
  quickly; on a public repo scheduled runs are free.
- `thinking: {"type":"disabled"}` on the coding endpoint measurably shortens
  reasoning (observed ~60 vs ~263 chars) but does not fully suppress it;
  per-run consumption stays around 40–50 output tokens.
