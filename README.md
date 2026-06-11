# AGENT//OS — Autonomous Lead Generation Agent

An open-source autonomous agent that finds leads, handles inbound, and drafts outreach — with a human-in-the-loop approval gate via Telegram.

Built with the raw Anthropic API tool use. Claude decides which tools to call based on your config.

If you need a custom tool for your business automation - send me an email irieid.pt@icloud.com

## How it works

```
agent.config.yaml        ← you define your ICP, tone, schedule, content strategy
       │
       ▼
Claude reads your config + available tools
Claude decides which tools to call and in what order
       │
       ├── search_linkedin       find leads matching your ICP
       ├── get_linkedin_profile  enrich each profile
       ├── web_search            research the person or company
       ├── read_sheet            skip if lead already in CRM
       ├── telegram_ask          ask you before sending anything
       ├── send_linkedin_invite  send connection request on approval
       ├── send_gmail            send email on approval
       ├── post_linkedin         publish LinkedIn post on approval
       ├── write_sheet           log everything to your CRM
       └── telegram_notify       send you summaries and updates
       │
       ├── You tap Send   → message goes out, lead logged
       ├── You tap Edit   → send your version, confirm, then posts
       └── You tap Reject → skipped, still logged

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/yourname/agent-os
cd agent-os
pip install -r requirements.txt
playwright install chromium
```

Node.js is required for Gmail and Sheets MCP servers.

### 2. Configure your agent

```bash
cp agent.config.yaml.example agent.config.yaml
```

Edit `agent.config.yaml` — this is the only file you need to change:

```yaml
me:
  name: "Your Name"
  role: "what you do"
  offer: "what you sell"

icp:
  roles: ["Founder", "Head of Growth"]
  industries: ["SaaS", "Marketing agency"]
  locations: ["London", "Berlin"]
  company_size: "10-100 employees"

tone:
  style: "direct and confident, founder to founder"
  avoid: ["I'd love to connect", "Hope this finds you well"]
```

### 3. Set credentials

```bash
cp .env.example .env
```

Fill in `.env`:

| Variable | Where to get it |
|----------|----------------|
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram |
| `TELEGRAM_CHAT_ID` | message @userinfobot |
| `LINKEDIN_EMAIL` | your LinkedIn login |
| `LINKEDIN_PASSWORD` | your LinkedIn password |
| `GOOGLE_SHEET_ID` | from your Sheet URL |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google Cloud Console → Service Accounts |

Share your Google Sheet with the service account email (Editor access).

### 4. Run

```bash
python main.py
```

The agent starts, Telegram bot comes online, scheduler activates.

---

## Using the agent

### Via Telegram

Send any message to your bot:

```
Find 10 e-commerce founders in Amsterdam and draft outreach
```

```
Check my inbox for leads from the last 24 hours
```

```
Research the top 5 no-code automation tools and send me a summary
```

Commands:
- `/prospect` — run prospecting now
- `/inbox` — check inbox now  
- `/status` — is the agent running?
- `/stop` — cancel current task

### Via API

```bash
curl -N -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Find 5 SaaS founders in Berlin", "mode": "prospect"}'
```

---

## Project structure

```
agent.config.yaml     ← your ICP, tone, schedule (edit this)
.env                  ← your credentials (never commit)
main.py               ← entry point

core/
  agent.py            ← the agent loop (Claude + tool use)
  config_loader.py    ← reads agent.config.yaml
  prompts.py          ← builds system prompt from your config
  executor.py         ← routes tool calls to implementations
  scheduler.py        ← cron jobs driven by config
  tool_definitions.py ← tool schemas Claude sees

tools/
  linkedin.py         ← Playwright browser automation
  gmail.py            ← Gmail MCP
  sheets.py           ← Google Sheets MCP
  telegram.py         ← approval gate + notifications
  web_search.py       ← DuckDuckGo

bot/
  receiver.py         ← Telegram command + message handler

api/
  app.py              ← FastAPI + SSE streaming endpoint
```

---

## Configuration reference

See `agent.config.yaml` — every field is commented.

Key settings:

```yaml
prospecting:
  leads_per_run: 5          # leads per scheduled run
  check_existing_crm: true  # skip leads already in Sheets
  auto_send_if_hot: false   # require approval for all leads

schedule:
  prospect_time: "09:00"    # daily run time
  inbox_interval_hours: 2   # inbox check frequency
```

---

## Production notes

- LinkedIn: keep `leads_per_run` at 5-10 to avoid account restrictions
- Store: the in-memory run store resets on restart — swap for Redis if needed
- Timezone: APScheduler uses server timezone — set your VPS timezone accordingly
- MCP servers: require Node.js — `npm` must be available in PATH
