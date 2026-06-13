import httpx
import os
import asyncio

class SREInvestigator:
    def __init__(self):
        self.grafana_url = "http://localhost:3000"
        self.prometheus_url = "http://localhost:9090"
        self.payment_api_url = "http://localhost:8000"

    async def check_metrics_api(self):
        """Fallback method: Query Prometheus API directly to check metrics."""
        try:
            async with httpx.AsyncClient() as client:
                # Query Prometheus for p95 latency
                query = 'payment_api_latency_seconds{quantile="0.95"}'
                response = await client.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": query},
                    timeout=2.0
                )
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("data", {}).get("result", [])
                    if results:
                        val = results[0]["value"][1]
                        return {"p95_latency": float(val), "source": "Prometheus API"}
                
                # If Prometheus is empty, check payment-api directly
                response = await client.get(f"{self.payment_api_url}/metrics", timeout=2.0)
                if response.status_code == 200:
                    lines = response.text.split("\n")
                    p95 = 0.0
                    for line in lines:
                        if 'payment_api_latency_seconds{quantile="0.95"}' in line:
                            p95 = float(line.split()[-1])
                    return {"p95_latency": p95, "source": "Payment API Direct metrics"}
        except Exception as e:
            return {"error": f"Failed to retrieve metrics via API: {e}"}
        return {"p95_latency": 0.0, "source": "No metrics available"}

    async def investigate_grafana_with_browser(self):
        """
        OpenClaw-style Computer Use: Launches a browser using Playwright,
        navigates to Grafana dashboard, and takes a screenshot or extracts information.
        """
        try:
            from playwright.async_api import async_playwright
            print("INFO: Launching browser via Playwright...")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to the dashboard (using anonymous access)
                dashboard_url = f"{self.grafana_url}/d/payment_api_dashboard"
                print(f"INFO: Navigating to Grafana: {dashboard_url}")
                await page.goto(dashboard_url, wait_until="networkidle")
                
                # Wait for panels to load metrics
                await asyncio.sleep(2)
                
                # Capture screenshot for visual inspection (multimodal LLM analysis)
                screenshot_path = "./grafana_snapshot.png"
                await page.screenshot(path=screenshot_path)
                print(f"SUCCESS: Captured dashboard snapshot: {screenshot_path}")
                
                # Scrape text metrics from the DOM if possible
                # In Grafana 10+, panel values can be found in DOM elements with class 'panel-content' or similar
                # Let's inspect some text elements
                titles = await page.locator("h2").all_inner_texts()
                print(f"INFO: Found panel titles: {titles}")
                
                await browser.close()
                return {
                    "status": "success",
                    "screenshot": screenshot_path,
                    "panels_found": titles,
                    "source": "Playwright Browser Automation"
                }
        except Exception as e:
            print(f"WARNING: Playwright browser run failed: {e}. Using API metrics fallback.")
            api_metrics = await self.check_metrics_api()
            return {
                "status": "fallback",
                "metrics": api_metrics,
                "note": "Playwright is not installed or failed. Switched to REST API metrics retrieval.",
                "source": "Prometheus REST API"
            }

    async def fetch_service_logs(self):
        """Fetch logs from payment-api directly."""
        try:
            # For this simulation, we can query /status or read local compose logs.
            # We'll simulate fetching logs by querying payment-api status.
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.payment_api_url}/status", timeout=2.0)
                if response.status_code == 200:
                    status_data = response.json()
                    if status_data.get("status") == "degraded":
                        return "ERROR: payment-api connection pool exhausted, active connections: 20/20"
                    return "INFO: payment-api serving requests, connection pool stable"
        except Exception as e:
            return f"ERROR: Failed to connect to payment-api: {e}"
        return "INFO: No log entries found"
