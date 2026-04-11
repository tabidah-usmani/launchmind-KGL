# LaunchMind — DocuSprint 🚀

## What is DocuSprint?

DocuSprint is a web-based tool for solo developers and open source maintainers that automatically generates a clean README, API documentation, and usage examples from their codebase. Users paste a GitHub repo link and receive production-ready documentation in seconds. Revenue comes from a freemium model — free for small repos, paid for unlimited access and custom templates.

---

## Agent Architecture

LaunchMind is a Multi-Agent System (MAS) where 5 autonomous LLM-powered agents collaborate to run DocuSprint as a micro-startup. Agents communicate via a Redis pub/sub message bus using structured JSON messages.

```
                        ┌─────────────────┐
                        │   CEO Agent     │
                        │  (Orchestrator) │
                        └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             ┌──────────┐ ┌──────────┐ ┌──────────┐
             │ Product  │ │ Engineer │ │Marketing │
             │  Agent   │ │  Agent   │ │  Agent   │
             └────┬─────┘ └────┬─────┘ └────┬─────┘
                  │            │             │
                  └────────────┴─────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │    QA Agent     │
                        │   (Reviewer)    │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   CEO Agent     │
                        │ (Final Summary) │
                        └─────────────────┘
```

### Agent Responsibilities

**CEO Agent** — The orchestrator. Receives the startup idea, decomposes it into tasks using an LLM, sends tasks to all sub-agents, reviews every output with LLM reasoning, sends revision requests if quality is poor, and posts the final summary to Slack.

**Product Agent** — Thinks like a product manager. Generates a structured product spec including value proposition, user personas, core features, and user stories. Sends the spec to both the Engineer and Marketing agents.

**Engineer Agent** — The builder. Reads the product spec and generates a complete HTML landing page, commits it to GitHub, creates an issue, and opens a pull request. All authored by `EngineerAgent`.

**Marketing Agent** — The growth marketer. Generates a tagline, product description, cold outreach email, and social media posts. Sends the email via SendGrid and posts a Block Kit message to Slack.

**QA Agent** — The reviewer. Reviews the HTML landing page and marketing copy against the product spec using an LLM. Posts inline review comments on the GitHub PR and sends a pass/fail verdict back to the CEO.

---

### Message Flow

```
CEO → PRODUCT       (task: decomposed startup idea)
CEO → ENGINEER      (task: build landing page)
CEO → MARKETING     (task: generate marketing copy)
PRODUCT → ENGINEER  (result: product spec JSON)
PRODUCT → MARKETING (result: product spec JSON)
PRODUCT → CEO       (confirmation: spec ready)
CEO → PRODUCT       (revision_request) ← if spec rejected
ENGINEER → CEO      (result: PR URL + issue URL)
CEO → MARKETING     (task: PR URL)
MARKETING → CEO     (result: marketing copy JSON)
CEO → QA            (task: HTML + copy + PR number)
QA → CEO            (result: pass/fail verdict)
CEO → ENGINEER      (revision_request) ← if QA fails
CEO → Slack         (final summary message)
```

### Feedback Loops

The system implements dynamic decision-making through two feedback loops:

**Loop 1 — Product Review:** CEO receives the product spec, sends it to the LLM for review, and if rejected sends a `revision_request` back to the Product agent with specific feedback. This repeats up to 6 times.

**Loop 2 — Engineer Review:** QA agent reviews the HTML landing page and if it fails, CEO sends a `revision_request` to the Engineer agent with specific issues listed. Engineer regenerates the HTML and QA reviews again.

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- Git
- WSL (for Redis on Windows) or Redis installed natively

### 1. Clone the repository
```bash
git clone https://github.com/tabidah-usmani/launchmind-KGL.git
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set environment variables

Copy the example env file:
```bash
copy .env.example .env
```

Open `.env` and fill in all values:
```
GROQ_API_KEY=your_groq_key_here
GITHUB_TOKEN=your_github_pat_here
GITHUB_REPO=tabidah-usmani/launchmind-KGL
SLACK_BOT_TOKEN=xoxb-your-slack-token-here
SENDGRID_API_KEY=SG.your-sendgrid-key-here
VERIFIED_EMAIL=your_verified_sender@email.com
TEST_EMAIL=your_test_inbox@email.com
```

### Getting API Keys

| Key | Where to get it |
|---|---|
| GROQ_API_KEY | console.groq.com → API Keys |
| GITHUB_TOKEN | github.com → Settings → Developer Settings → Personal Access Tokens (classic) → repo + workflow scopes |
| SLACK_BOT_TOKEN | api.slack.com → Your App → OAuth & Permissions |
| SENDGRID_API_KEY | app.sendgrid.com → Settings → API Keys |
| VERIFIED_EMAIL | Your SendGrid verified sender email |
| TEST_EMAIL | Any email address you want to receive the cold outreach email |

### 4. Start Redis

**Windows (via WSL):**
```bash
# Open WSL terminal
sudo service redis-server start
redis-cli ping  # should print PONG
```

**Mac/Linux:**
```bash
brew install redis
redis-server
```

### 5. Run the system
```bash
python main.py
```

The full pipeline runs automatically — no manual intervention needed. All agent messages print to the terminal in real time.

---

## Platform Integrations

### GitHub
- **Engineer Agent** creates a new branch called `agent-landing-page`
- **Engineer Agent** commits `index.html` (HTML landing page) authored by `EngineerAgent <agent@launchmind.ai>`
- **Engineer Agent** creates a GitHub issue with an LLM-generated description
- **Engineer Agent** opens a pull request with an LLM-generated title and body
- **QA Agent** posts 2 inline review comments on the pull request via the GitHub Reviews API

### Slack
- **Marketing Agent** posts a Block Kit formatted launch announcement to `#launches` including the product tagline, description, and GitHub PR link
- **CEO Agent** posts a final summary Block Kit message to `#launches` after the full pipeline completes, including the startup idea, tagline, QA verdict, and PR link

### SendGrid (Email)
- **Marketing Agent** sends a cold outreach email to the target inbox
- Both the email subject line and body are generated entirely by the LLM based on the product spec
- Sent from a verified SendGrid sender address stored in environment variables

### Groq (LLM API)
- All 5 agents use the Groq API with `llama-3.3-70b-versatile` model
- Used for: task decomposition, product spec generation, HTML landing page generation, marketing copy generation, CEO output review, and QA review
- No hardcoded outputs — all content is LLM generated at runtime

### Redis (Message Bus)
- All inter-agent messages are published to Redis pub/sub channels
- Each agent has its own named channel: `product`, `engineer`, `marketing`, `ceo`, `qa`
- Messages are stored in Redis lists for retrieval
- Full message history persisted in Redis and printed at end of each run

---

## Message Schema

Every message passed between agents follows this required schema:

```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "from_agent": "ceo",
  "to_agent": "product",
  "message_type": "task",
  "payload": {
    "idea": "DocuSprint startup idea...",
    "focus": "Define user personas and top 5 features"
  },
  "timestamp": "2026-03-28T17:35:15.357193Z",
  "parent_message_id": null
}
```

Message types used: `task`, `result`, `revision_request`, `confirmation`

---

## Repository Structure

```
launchmind-KGL/
├── agents/
│   ├── ceo_agent.py          # CEO orchestrator agent
│   ├── product_agent.py      # Product manager agent
│   ├── engineer_agent.py     # Engineer agent
│   ├── marketing_agent.py    # Marketing agent
│   └── qa_agent.py           # QA reviewer agent
├── main.py                   # Single entry point — runs entire system
├── message_bus.py            # Redis pub/sub message bus implementation
├── requirements.txt          # All dependencies
├── .env.example              # Template for environment variables
├── .gitignore                # Excludes .env from version control
└── README.md                 # This file
```

---

## Links

- **GitHub Repository:** https://github.com/tabidah-usmani/launchmind-KGL
- **GitHub PR created by Engineer Agent:** https://github.com/tabidah-usmani/launchmind-KGL/pull/88

### Slack Bot in Action

The LaunchMind bot posts two messages to the `#launches` channel during each run:

1. **Marketing Agent** — Launch announcement with tagline, product description, and PR link
2. **CEO Agent** — Final summary with QA verdict, tagline, and pipeline completion status

Both messages use Slack Block Kit formatting.

---

## Team

| Member | Agent(s) | Responsibility |
|---|---|---|
| Tabidah Usmani | CEO Agent | Orchestration, task decomposition, LLM review, feedback loops |
| Umema Asher | Product Agent + Engineer Agent | Product spec generation, HTML landing page, GitHub integration |
| Hamza Asad | Marketing Agent + QA Agent | Marketing copy, email, Slack posting, QA review |

---

