import argparse
import asyncio
import os
import sys
import httpx
from agent.memory import SREMemory
from agent.investigator import SREInvestigator
from agent.planner import SREPlanner
from agent.reporter import SREReporter

# Initialize components
memory = SREMemory()
investigator = SREInvestigator()
planner = SREPlanner()
reporter = SREReporter()

async def run_learn(text: str):
    print(f"\n[Learning Phase] Storing incident resolution in memory:")
    print(f"Content: \"{text}\"")
    memory.add(text)
    print("Memory successfully stored.")

async def run_recall(query: str):
    print(f"\n[Retrieval Phase] Searching memory for query: \"{query}\"")
    results = memory.search(query)
    if not results:
        print("No matching memories found.")
    for idx, r in enumerate(results):
        print(f"Result {idx+1}: {r}")

async def run_investigate():
    print(f"\n[Observation Phase] Running metrics investigation...")
    metrics_result = await investigator.investigate_grafana_with_browser()
    print(f"Metrics Status: {metrics_result.get('status')}")
    print(f"Metrics Source: {metrics_result.get('source')}")
    
    if "metrics" in metrics_result:
        print(f"Parsed Metrics: {metrics_result['metrics']}")
    elif "panels_found" in metrics_result:
        print(f"Grafana Panels Found: {metrics_result['panels_found']}")
        
    logs = await investigator.fetch_service_logs()
    print(f"Service Logs Snippet:\n{logs}")
    return metrics_result, logs

async def run_auto_sre(alert_query: str):
    print("=" * 60)
    print(f"🚨 ALERT TRIGGERED: {alert_query}")
    print("=" * 60)
    
    # 1. Retrieve historical incident context from memory
    print("\nSTEP 1: Checking long-term memory for past occurrences...")
    past_incidents = memory.search(alert_query)
    print(f"Found {len(past_incidents)} relevant past incident memories.")
    for idx, r in enumerate(past_incidents):
        print(f" - Memory {idx+1}: {r[:120]}...")

    # 2. Observe metrics and logs
    print("\nSTEP 2: Executing browser/API investigation of dashboards...")
    metrics, logs = await run_investigate()

    # 3. Analyze and Plan
    print("\nSTEP 3: Sending diagnostic data to Gemini Planner...")
    analysis = planner.analyze(alert_query, past_incidents, metrics, logs)
    print(analysis)

    # 4. Remediation (Action)
    print("\nSTEP 4: Executing remediation action...")
    action_taken = "No action taken. Waiting for operator confirmation."
    
    # Parse potential resolution from analysis
    if "Database Connection Pool" in analysis:
        # Resolve via REST call to payment-api to reset DB state
        print("🔧 Action: Resetting payment-api database pool exhaustion state...")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post("http://localhost:8000/inject-db-exhaustion?active=false", timeout=3.0)
                if resp.status_code == 200:
                    action_taken = "Successfully resolved Database Pool Exhaustion via API reset."
                    print(f"✅ {action_taken}")
                else:
                    action_taken = "Failed to reset database pool exhaustion state."
                    print(f"❌ {action_taken}")
        except Exception as e:
            action_taken = f"Network failure calling payment-api reset endpoint: {e}"
            print(f"❌ {action_taken}")
            
    elif "Dependency Outage" in analysis or "order-api" in analysis.lower():
        # Inform how to resolve or attempt restart
        print("🔧 Action Suggestion: Restarting order-api container...")
        # In a real environment, we can run: os.system("docker compose restart order-api")
        # Let's execute the command or tell the user we are doing it
        exit_code = os.system("docker compose restart order-api 2>/dev/null")
        if exit_code == 0:
            action_taken = "Executed 'docker compose restart order-api' successfully."
            print(f"✅ {action_taken}")
        else:
            action_taken = "Attempted 'docker compose restart order-api' but docker-compose command was not available."
            print(f"⚠️ {action_taken}")
    else:
        print("🤷 Unknown root cause. Requiring human operator manual runbooks.")
        action_taken = "Manual intervention required. Logged incident details."

    # 5. Store new findings into memory if we learned anything new
    print("\nSTEP 5: Updating memory with resolution details...")
    new_memory = f"Incident Alert: {alert_query}. Root Cause identified: {analysis.split('### Diagnosis')[1].split('###')[0].strip() if '### Diagnosis' in analysis else 'System degradation'}. Action Taken: {action_taken}."
    memory.add(new_memory)
    print("✅ Memory updated.")

    # 6. Generate incident report
    print("\nSTEP 6: Creating incident report...")
    report_file = reporter.generate_report(service="payment-api", diagnosis=analysis, action_taken=action_taken)
    print(f"✅ Incident report written to {report_file}")
    print("\n🎯 Autonomous SRE Loop Completed.")
    print("=" * 60)

async def trigger_outage(outage_type: str):
    async with httpx.AsyncClient() as client:
        if outage_type == "db":
            print("Injecting database connection pool exhaustion to payment-api...")
            resp = await client.post("http://localhost:8000/inject-db-exhaustion?active=true")
            print(resp.json())
        elif outage_type == "dependency":
            print("Stopping order-api container to trigger dependency outage...")
            os.system("docker compose stop order-api")
        elif outage_type == "clear":
            print("Clearing all injected outages...")
            await client.post("http://localhost:8000/inject-db-exhaustion?active=false")
            os.system("docker compose start order-api")
        else:
            print("Unknown outage type. Use 'db', 'dependency', or 'clear'.")

def main():
    parser = argparse.ArgumentParser(description="Autonomous SRE Agent")
    parser.add_argument("--action", choices=["learn", "recall", "investigate", "auto-sre", "outage"], required=True)
    parser.add_argument("--text", type=str, help="Text to learn (for learn action)")
    parser.add_argument("--query", type=str, help="Search query (for recall / auto-sre action)")
    parser.add_argument("--type", choices=["db", "dependency", "clear"], help="Outage type (for outage action)")
    
    args = parser.parse_args()
    
    if args.action == "learn":
        if not args.text:
            print("Error: --text is required for learn action.")
            sys.exit(1)
        asyncio.run(run_learn(args.text))
        
    elif args.action == "recall":
        if not args.query:
            print("Error: --query is required for recall action.")
            sys.exit(1)
        asyncio.run(run_recall(args.query))
        
    elif args.action == "investigate":
        asyncio.run(run_investigate())
        
    elif args.action == "auto-sre":
        query = args.query or "payment-api response latency > 5s"
        asyncio.run(run_auto_sre(query))
        
    elif args.action == "outage":
        if not args.type:
            print("Error: --type is required for outage action.")
            sys.exit(1)
        asyncio.run(trigger_outage(args.type))

if __name__ == "__main__":
    main()
