# Memory to Action: Building an Autonomous SRE Agent with Mem0 and OpenClaw

This repository contains the code and lab exercises for the **From Memory to Action: Building an Autonomous SRE Agent with Mem0 and OpenClaw** hands-on codelab workshop.

---

## 🏗️ Architecture Overview

The system consists of two main parts:
1. **Lab Environment (Docker Compose)**:
   - **Payment API**: Mock microservice that processes payments and records metrics. Includes a backend dependency and endpoints to inject simulated failures (latency/errors).
   - **Order API**: Backend verification dependency service.
   - **Prometheus**: Metrics server scraping Payment API metrics.
   - **Grafana**: Dashboard visualizing service response times and errors (configured with anonymous admin access for automated exploration).

2. **SRE Agent**:
   - **Memory Layer (`mem0`)**: Storing and searching past incident logs and resolution playbooks.
   - **Investigation Layer (Playwright/OpenClaw)**: Automating browser interactions with Grafana to observe status, with direct REST API fallbacks.
   - **Reasoning Layer (Gemini/LLM)**: Correlating current observations with historical memories to diagnose issues.
   - **Remediation & Reporting Layer**: Automatically fixing problems and generating markdown reports.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js (for OpenClaw gateway runtime)
- Docker & Docker Compose
- Playwright system dependencies (installed via `playwright install` or fallback is used)

### 1. Set Up Environment
Clone the repository, create a Python virtual environment, install dependencies, and install OpenClaw globally:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (optional, falls back to API scraping if not installed)
playwright install chromium

# Install OpenClaw globally
npm install -g openclaw@latest
```

Copy the `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
Provide your `GEMINI_API_KEY` and your `MEM0_API_KEY` (from the Mem0 Cloud Platform) in the `.env` file. If no API keys are set, the SRE agent gracefully falls back to local file memory and rule-based planning.

### 2. Start the Lab Environment
Spin up the mock microservices and monitoring stack:

```bash
docker compose up -d
```

Verify services are running:
- **Payment API**: [http://localhost:8000/status](http://localhost:8000/status) (Metrics at `/metrics`)
- **Prometheus**: [http://localhost:9090](http://localhost:9090)
- **Grafana Dashboard**: [http://localhost:3000/d/payment_api_dashboard](http://localhost:3000/d/payment_api_dashboard)

---

## 🛠️ Lab Exercises

### Lab 1: Store Historical Playbooks (Memory Phase)
Teach the agent how to resolve database connection pool issues:
```bash
python -m agent.main --action learn --text "Incident: payment-api timeout or database pool exhausted. Cause: Database connection pool size too small. Solution: Reset the database pool state via REST API, increase pool size."
```
Search memory to verify recall:
```bash
python -m agent.main --action recall --query "payment-api latency high"
```

### Lab 2: Inject Outage & Investigate Dashboard (Observation Phase)
Inject a database latency outage to trigger alert:
```bash
python -m agent.main --action outage --type db
```
Trigger agent to investigate metrics:
```bash
python -m agent.main --action investigate
```
*Observe that the agent launches a browser, navigates Grafana, captures a screenshot, and parses latency numbers.*

### Lab 3: Run the Autonomous SRE Loop (Memory to Action)
Now run the full SRE loop where the agent:
1. Receives an alert query.
2. Recalls past resolutions.
3. Investigates metrics and logs.
4. Diagnoses the issue.
5. Remediates the outage automatically.
6. Stores the run results back into long-term memory.
7. Generates an incident report.

```bash
python -m agent.main --action auto-sre --query "payment-api latency high or connection pool errors"
```

Check the generated report in `./reports/`.

### Lab 4: OpenClaw Custom Skill Integration
OpenClaw loads skills dynamically from your workspace. We have registered our SRE Agent loop as a capability within the OpenClaw runtime under `skills/sre-incident-handler/SKILL.md`.

To boot the OpenClaw gateway and make it aware of our SRE skill:
```bash
openclaw onboard
openclaw start
```
Interact with the OpenClaw gateway via messaging clients (Slack/Telegram) by asking it to: *"Investigate payment-api response latency."* OpenClaw will read the skill details and invoke our Python runner autonomously!

---

## 🛠️ Cleanup
Clear the outages and shut down the environment:
```bash
python -m agent.main --action outage --type clear
docker compose down -v
```
