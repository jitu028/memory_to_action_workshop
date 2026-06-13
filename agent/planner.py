import os
from dotenv import load_dotenv

load_dotenv()

class SREPlanner:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.use_llm = False
        
        if self.api_key:
            try:
                # Try new google-genai SDK
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                self.sdk_type = "genai"
                self.use_llm = True
                print("INFO: Gemini GenAI SDK initialized successfully.")
            except ImportError:
                try:
                    # Try legacy google-generativeai SDK
                    import google.generativeai as genai
                    genai.configure(api_key=self.api_key)
                    self.model = genai.GenerativeModel('gemini-2.5-flash')
                    self.sdk_type = "legacy"
                    self.use_llm = True
                    print("INFO: Legacy Google GenerativeAI SDK initialized successfully.")
                except Exception as e:
                    print(f"WARNING: LLM SDKs failed to load ({e}). Using rule-based fallback planner.")
        else:
            print("WARNING: GEMINI_API_KEY not found in environment. Using rule-based fallback planner.")

    def analyze(self, query: str, memories: list, metrics: dict, logs: str):
        """Analyze the query, memories, metrics, and logs to diagnose the issue."""
        if not self.use_llm:
            return self._fallback_rule_based_analysis(query, memories, metrics, logs)
            
        prompt = f"""
You are an expert Autonomous SRE Agent. Your task is to analyze a production service incident.

USER QUERY: {query}

HISTORICAL INCIDENT MEMORIES:
{chr(10).join([f"- {m}" for m in memories]) if memories else "No relevant historical incidents found in memory."}

CURRENT DASHBOARD METRICS:
{metrics}

SERVICE LOGS Snippet:
{logs}

Analyze the data:
1. Determine if this incident matches any historical incident retrieved from memory.
2. Formulate a diagnosis based on metrics and logs.
3. Suggest a clear, actionable remediation.

Format your output in clean Markdown with sections:
### Diagnosis
### Match with Memory
### Remediation Steps
### Confidence Score (0-100%)
"""

        try:
            if self.sdk_type == "genai":
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                return response.text
            else:
                response = self.model.generate_content(prompt)
                return response.text
        except Exception as e:
            print(f"ERROR: LLM generation failed ({e}). Falling back to rule-based planner.")
            return self._fallback_rule_based_analysis(query, memories, metrics, logs)

    def _fallback_rule_based_analysis(self, query: str, memories: list, metrics: dict, logs: str):
        """Rule-based backup analysis when API keys or LLM SDKs are unavailable."""
        latency = metrics.get("p95_latency", 0.0)
        if metrics.get("metrics"):
            latency = metrics["metrics"].get("p95_latency", 0.0)
            
        has_memory_match = len(memories) > 0
        memory_summary = memories[0] if has_memory_match else "None"
        
        # Simple heuristics
        if "exhausted" in logs or latency > 4.0:
            diagnosis = "Database Connection Pool Exhaustion. The payment-api is experiencing high response times (> 5s) due to unavailable database connections."
            remediation = "1. Scale up database pool size in service config.\n2. Restart the payment-api container to release locked connections."
            confidence = "90% (based on metrics + logs)"
        elif "unavailable" in logs or "Connection refused" in logs or "502" in query:
            diagnosis = "Dependency Outage. payment-api failed to verify order because order-api service is down or unreachable."
            remediation = "1. Verify if order-api is running: `docker compose ps`.\n2. Restart order-api: `docker compose restart order-api`."
            confidence = "85% (based on dependency call failure)"
        else:
            diagnosis = "Unknown system degradation. High latency detected."
            remediation = "1. Check service logs via `docker compose logs`.\n2. Check dependencies health."
            confidence = "50%"

        return f"""
### Diagnosis
{diagnosis}

### Match with Memory
- Matches historical incident: {has_memory_match}
- Detail: {memory_summary}

### Remediation Steps
{remediation}

### Confidence Score (Rule-Based Fallback)
{confidence}
"""
