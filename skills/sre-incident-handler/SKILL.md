---
name: sre_incident_handler
description: Diagnose and autonomously remediate Payment API outages, database pool exhaustion, and dependency failures using the local SRE agent loop.
---

# SRE Incident Handler Skill

This skill allows the OpenClaw agent to investigate production incidents on the Payment API microservices stack.

## Usage Instructions

When the user alerts you about an incident, degraded status, or high latency on the `payment-api` service (e.g., "payment-api latency > 5s" or "Investigate payment service degradation"), execute the local autonomous SRE Agent loop.

### Command Execution

Run the SRE Agent script from the repository root directory:

```bash
.venv/bin/python -m agent.main --action auto-sre --query "<alert_query>"
```

### Parameters
*   `alert_query`: The specific symptom or alert reported by the user (e.g. "payment-api latency high" or "connection pool exhausted").

### Expected Output
The command will run the full SRE loop:
1. Search Mem0 memory playbooks.
2. Launch a Playwright browser to investigate Grafana.
3. Call Gemini to diagnose root cause.
4. Execute remediation (API reset or container restart).
5. Generate an incident report under `./reports/`.

Report the final result, root cause diagnosis, and remediation actions back to the user.
