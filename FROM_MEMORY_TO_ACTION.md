summary: Build an Autonomous SRE Agent that remembers historical outages, inspects monitoring dashboards using computer-use, and executes auto-remediation.
id: memory-to-action-sre-agent
categories: AI, SRE, Agent
environments: Web
status: Published
feedback link: https://github.com/your-username/memory-to-action-workshop/issues
tags: Mem0, OpenClaw, Agentic AI, SRE, Gemini, DevOps, Playwright, Docker

# From Memory to Action: Building an Autonomous SRE Agent with Mem0 and OpenClaw

## 1. Overview & Objectives
Duration: 5

Standard AI chatbots are reactive and context-isolated. They cannot remember what happened yesterday, learn from operational experiences, or interact directly with graphical user interfaces like monitoring dashboards. 

In this workshop, you will move beyond simple text chatbots and build an **Autonomous SRE Agent** that:
1. **Remembers** historical outages and remediation patterns using **Mem0**.
2. **Observes** dashboards (Grafana) using computer-use browser automation (**OpenClaw / Playwright**).
3. **Decides** on root causes and resolutions using the **Gemini model**.
4. **Remediates** the issue and logs findings back into long-term memory.

### What You Will Build
You will build a project structured as follows:
- **Mock Service Environment**: Docker Compose environment containing a Python Payment API, Order API, Prometheus, and Grafana.
- **SRE Memory Module**: Interface with Mem0 to persist resolution playbooks.
- **SRE Investigator Module**: Playwright-based browser driver that navigates Grafana.
- **SRE Planner Module**: Gemini LLM connector to orchestrate reasoning.
- **SRE Reporter Module**: Generator of Markdown incident reports.

---

### Architecture diagram
```text
                    ALERT TRIGGERED
                          │
                          ▼
                  SRE Agent Runtime
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
     Mem0 Memory    Gemini Planner   OpenClaw Browser
  (Past Incidents)    (Reasoning)       (Grafana UI)
         │                │                │
         ▼                ▼                ▼
    Local SQLite     RCA & Action    Execute Actions
         │                │                │
         └────────────────┼────────────────┘
                          │
                          ▼
           Docker Compose Lab Environment
         (Payment API, Prometheus, Grafana)
```

---

## 2. Prerequisites & Setup
Duration: 10

### System Requirements
Before starting, ensure you have:
- **Python 3.10+** installed.
- **Docker & Docker Compose** running on your laptop.
- A **Gemini API Key** (Optional. If not set, the agent uses a rule-based fallback logic so you can still complete the entire lab).

### Project Layout
Your workspace directory should look like this:
```text
sre-agent/
├── agent/
│   ├── memory.py        # Mem0 Integration
│   ├── investigator.py  # Playwright Browser / API Scraping
│   ├── planner.py       # Gemini Reasoning
│   ├── reporter.py      # Markdown Incident Reporter
│   └── main.py          # CLI Runner & Autonomous Loop
├── services/
│   ├── payment_api/     # Mock Payment Service
│   └── order_api/       # Mock Dependency Service
├── monitoring/
│   ├── prometheus/      # Scrapers and Configuration
│   └── grafana/         # Provisioning Datasources and Dashboards
├── docker-compose.yaml
└── requirements.txt
```

### Install Dependencies
Run the following commands to initialize your virtual environment and install OpenClaw globally:

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required Python packages
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium

# Install the actual OpenClaw platform globally
npm install -g openclaw@latest

# Install and configure the Mem0 memory plugin for OpenClaw
openclaw plugins install @mem0/openclaw-mem0
openclaw mem0 init --api-key your_mem0_api_key_here
```

### Configure Environment Variables
Copy `.env.example` to `.env` and configure your keys:
```bash
# Set your Gemini API key for reasoning
GEMINI_API_KEY=your_gemini_api_key_here

# Set your Mem0 Platform key to use actual cloud memory (falls back to OpenClaw CLI)
MEM0_API_KEY=your_mem0_api_key_here
```
Note: If the OpenClaw Mem0 plugin is initialized, the SRE Agent will automatically detect it and query memories through the OpenClaw CLI, ensuring shared memory across your CLI runs and chat sessions!

---

## 3. The Lab Environment
Duration: 15

To test our SRE agent, we need a realistic system. We run a mock containerized setup with Docker Compose.

### Docker Compose Configuration (`docker-compose.yaml`)
Our stack includes the **Payment API** (monitored service), **Order API** (its dependency), **Prometheus** (collecting metrics), and **Grafana** (dashboard).

To launch the stack, execute:
```bash
docker compose up -d
```

### Checking the Metrics
1. Navigate to the Payment API status: [http://localhost:8000/status](http://localhost:8000/status).
2. Look at raw Prometheus metrics exposed by the service: [http://localhost:8000/metrics](http://localhost:8000/metrics).
3. Access the Grafana Dashboard: [http://localhost:3000/d/payment_api_dashboard](http://localhost:3000/d/payment_api_dashboard). Anonymous access has been pre-configured so you don't need a username/password!

---

## 4. Lab 1: Storing Playbooks in Mem0 (Memory)
Duration: 15

Traditional RAG searches static document vaults. **Mem0** provides dynamic, user-centric memory that adapts over time. 

In this lab, we leverage the **OpenClaw Mem0 Plugin** to share memory across the SRE Agent and our OpenClaw natural language assistant.

### Importing Workspace Profiles & Diaries
OpenClaw organizes user context using workspace files (`SOUL.md`, `IDENTITY.md`, `USER.md`). We can import these profiles directly into Mem0 using the OpenClaw CLI.

First, verify that your Mem0 plugin is connected:
```bash
openclaw mem0 status
```
It should print `Connected to Mem0`.

To build the import file from your workspace:
```bash
python3 build_import.py
```
This parses the workspace markdown files, chunks them by heading, and generates `/tmp/mem0_import.json`. Now, import them into your Mem0 Platform account:
```bash
openclaw mem0 import /tmp/mem0_import.json
```

Verify that the memories are searchable:
```bash
openclaw mem0 search "preferences"
```

### Programmatic Integration in SRE Agent
Let's look at `agent/memory.py`. It automatically detects if the OpenClaw Mem0 plugin is active. If so, it uses the `openclaw mem0` commands under the hood to store and query playbooks. Otherwise, it falls back to the `mem0ai` client or local files.

### Exercise: Storing your first resolution playbook
We will teach our SRE Agent how to handle database connection issues. Run this command in your terminal:

```bash
python -m agent.main --action learn --text "Incident: payment-api timeout or database pool exhausted. Root Cause: Database connection pool size too small. Resolution: Reset the database pool state via REST API, increase pool size."
```

### Exercise: Verifying memory recall
Test if the agent can retrieve this playbook when queried about a related latency issue:

```bash
python -m agent.main --action recall --query "payment-api latency high"
```

You will see the SRE agent successfully recall the exact text you stored, even though the query used different words ("latency high" instead of "timeout").

---

## 5. Lab 2: Autonomous Dashboard Investigation (OpenClaw / Browser)
Duration: 20

Next, we teach our agent to observe. The `agent/investigator.py` module uses **Playwright** (simulating OpenClaw's browser-automation interface) to open a headless browser, navigate to the Grafana dashboard, wait for the charts to render, and take a screenshot.

### Exercise: Triggering an Outage
Let's inject database connection exhaustion into our Payment API:

```bash
python -m agent.main --action outage --type db
```
Now, verify the service is degraded by opening [http://localhost:8000/status](http://localhost:8000/status). You should see:
```json
{
  "status": "degraded",
  "db_exhaustion_active": true
}
```

### Exercise: Running the browser investigation
Let the agent open Grafana and inspect the metrics:

```bash
python -m agent.main --action investigate
```

The agent will launch a headless browser, navigate to [http://localhost:3000/d/payment_api_dashboard](http://localhost:3000/d/payment_api_dashboard), and save a snapshot to `./grafana_snapshot.png`. If you check your workspace, you will find this screenshot rendering the Grafana graphs!

---

## 6. Lab 3: Reasoning and Diagnosing (Gemini Planner)
Duration: 15

Now that the agent has access to **Memory** (Mem0 playbooks) and **Observations** (Grafana metrics & logs), it needs to reason.

The `agent/planner.py` module uses the **Gemini 2.5 Flash model** via the new `google-genai` SDK to examine:
1. Stored memory playbooks.
2. Active metrics (latencies).
3. System logs.

Gemini compares these inputs and performs a root-cause diagnosis. If a memory playbook matches the current symptom, it prepares the specific remediation steps.

---

## 7. Lab 4: The Complete Autonomous SRE Loop
Duration: 25

We will now execute the full end-to-end autonomous cycle:
1. **Detect / Alert**: Receive an alert query ("payment-api response latency > 5s").
2. **Recall**: Search Mem0 memory for past similar outages.
3. **Investigate**: Scrape metrics and pull logs.
4. **Reason**: Call Gemini to correlate observations with memories.
5. **Act**: Reset the payment-api db state via API.
6. **Learn**: Add the new incident resolution history to Mem0.
7. **Report**: Create an executive report.

### Exercise: Running the Autonomous Agent
With the DB outage still active, run the full agent command:

```bash
python -m agent.main --action auto-sre --query "payment-api latency high or connection pool errors"
```

### Reviewing the Output
Watch the console output. You will see:
1. The agent searching memory and finding our playbook.
2. The agent taking a Grafana snapshot and pulling logs.
3. Gemini diagnosing database connection pool exhaustion.
4. The agent **automatically executing** the API call to clear the outage.
5. The agent generating a report.

Inspect the generated Markdown report under `./reports/incident_report_payment-api_*.md`. It contains a formal incident breakdown!

Verify that the Payment API is now healthy again by opening [http://localhost:8000/status](http://localhost:8000/status). It should return `"healthy"`.

---

## 8. OpenClaw Custom Skill Integration
Duration: 10

OpenClaw loads skills dynamically from the `skills/` directory of its workspace. We have pre-configured a custom skill to hook our autonomous Python SRE loop directly into the OpenClaw agent runtime.

### Onboarding the Custom Skill
Copy the skill configuration into your OpenClaw workspace:
```bash
mkdir -p ~/.openclaw/workspace/skills/sre-incident-handler
cp skills/sre-incident-handler/SKILL.md ~/.openclaw/workspace/skills/sre-incident-handler/SKILL.md
```

To start the OpenClaw gateway and load this skill:

```bash
# Onboard and start the OpenClaw gateway
openclaw onboard
openclaw gateway run --force --allow-unconfigured
```

When you interact with the OpenClaw gateway (via Telegram, Slack, or WhatsApp) and ask it to *"Investigate payment-api response latency"*, OpenClaw will read the `SKILL.md` instructions, invoke our Python script `.venv/bin/python -m agent.main --action auto-sre --query ...`, and report the visual Grafana diagnostics and root-cause analysis back to your messaging client!

---

## 9. Summary & Takeaways
Duration: 5

Congratulations! You have built a fully functional Autonomous SRE Agent using actual Mem0 Platform memory and integrated it into the OpenClaw runtime.

### Key Learnings
- **Long-term Agent Memory**: Actual Mem0 Platform Cloud keeps persistent history across runs and sessions, allowing the SRE agent to continuously learn from incidents.
- **UI Automation (Computer Use)**: Playwright replicates the core browser-driving engine that allows OpenClaw to analyze legacy dashboards like Grafana.
- **OpenClaw Skill Architecture**: Workspace skills enable you to wrap existing CLI tools, Python scripts, or complex loops and expose them instantly to natural language gateways.

### Clean Up the Environment
To close down all Docker containers, run:
```bash
python -m agent.main --action outage --type clear
docker compose down -v
```
