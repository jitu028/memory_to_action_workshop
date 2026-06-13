import os
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()

class SREMemory:
    def __init__(self):
        self.use_openclaw_cli = False
        self.use_mem0 = False
        self.use_client = False
        
        # 1. Check if OpenClaw Mem0 CLI is available and connected
        try:
            res = subprocess.run(["openclaw", "mem0", "status"], capture_output=True, text=True, check=False)
            if res.returncode == 0 and "Connected to Mem0" in res.stdout:
                self.use_openclaw_cli = True
                print("INFO: OpenClaw Mem0 Plugin detected and active. Using OpenClaw CLI for memory operations.")
                return
        except Exception:
            pass

        # 2. Fallback to direct Mem0 Platform Client (Cloud Platform) if API Key is set
        if os.getenv("MEM0_API_KEY"):
            try:
                from mem0 import MemoryClient
                self.memory = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
                self.use_client = True
                self.use_mem0 = True
                print("INFO: Mem0 Platform MemoryClient initialized successfully.")
                return
            except Exception as e:
                print(f"WARNING: Could not initialize Mem0 MemoryClient ({e}). Attempting local fallback.")

        # 3. Fallback to local open-source Mem0 configuration if API key not present
        try:
            from mem0 import Memory
            
            # Configure Mem0 to use Gemini or OpenAI based on env keys
            config = {}
            if os.getenv("GEMINI_API_KEY"):
                config = {
                    "vector_store": {
                        "provider": "chroma",
                        "config": {
                            "collection_name": "sre_agent_memory",
                            "path": "./.mem0_vector_db"
                        }
                    },
                    "llm": {
                        "provider": "gemini",
                        "config": {
                            "model": "gemini-2.5-flash",
                            "api_key": os.getenv("GEMINI_API_KEY")
                        }
                    },
                    "embedder": {
                        "provider": "gemini",
                        "config": {
                            "model": "text-embedding-004",
                            "api_key": os.getenv("GEMINI_API_KEY")
                        }
                    }
                }
            elif os.getenv("OPENAI_API_KEY"):
                config = {
                    "vector_store": {
                        "provider": "chroma",
                        "config": {
                            "collection_name": "sre_agent_memory",
                            "path": "./.mem0_vector_db"
                        }
                    },
                    "llm": {
                        "provider": "openai",
                        "config": {
                            "model": "gpt-4o-mini",
                            "api_key": os.getenv("OPENAI_API_KEY")
                        }
                    }
                }
            
            if config:
                self.memory = Memory.from_config(config)
            else:
                self.memory = Memory() # Default settings
            self.use_mem0 = True
            print("INFO: Mem0 Local vector db initialized successfully.")
        except Exception as e:
            print(f"WARNING: Could not initialize Mem0 Local Vector DB ({e}). Falling back to Local File Memory.")
            self.fallback_db_path = "./local_sre_memory.json"
            if not os.path.exists(self.fallback_db_path):
                with open(self.fallback_db_path, "w") as f:
                    json.dump([], f)

    def add(self, text: str, user_id: str = "sre_agent"):
        """Adds a memory about an incident or resolution."""
        if self.use_openclaw_cli:
            try:
                cmd = ["openclaw", "mem0", "add", text, "--user-id", user_id]
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    return {"message": "Memory added via OpenClaw CLI"}
                else:
                    print(f"WARNING: OpenClaw CLI add returned non-zero code {res.returncode}: {res.stderr}")
            except Exception as e:
                print(f"WARNING: OpenClaw CLI add failed: {e}. Falling back.")

        if self.use_mem0:
            return self.memory.add(text, user_id=user_id)
        else:
            # Fallback local file memory
            with open(self.fallback_db_path, "r") as f:
                memories = json.load(f)
            memories.append({"user_id": user_id, "text": text})
            with open(self.fallback_db_path, "w") as f:
                json.dump(memories, f, indent=2)
            return {"message": "Memory added to fallback file DB"}

    def search(self, query: str, user_id: str = "sre_agent"):
        """Searches memory for relevant past incidents."""
        if self.use_openclaw_cli:
            try:
                cmd = ["openclaw", "mem0", "search", query, "--user-id", user_id, "--json"]
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    if isinstance(data, dict) and "results" in data:
                        return [item["memory"] for item in data["results"] if "memory" in item]
                else:
                    print(f"WARNING: OpenClaw CLI search returned non-zero code {res.returncode}: {res.stderr}")
            except Exception as e:
                print(f"WARNING: OpenClaw CLI search failed: {e}. Falling back.")

        if self.use_mem0:
            results = self.memory.search(query, user_id=user_id)
            # Normalize results to a list of dicts with 'text'
            normalized = []
            for r in results:
                # Mem0 returns list of dicts, sometimes with 'memory' or 'text' key
                if isinstance(r, dict):
                    normalized.append(r.get("memory", r.get("text", r.get("memory_text", str(r)))))
                elif isinstance(r, str):
                    normalized.append(r)
            return normalized
        else:
            # Basic fallback keyword search
            try:
                with open(self.fallback_db_path, "r") as f:
                    memories = json.load(f)
            except Exception:
                return []
            results = []
            keywords = query.lower().split()
            for m in memories:
                if m.get("user_id") == user_id:
                    score = sum(1 for kw in keywords if kw in m.get("text", "").lower())
                    if score > 0:
                        results.append(m.get("text", ""))
            return results

    def list_all(self, user_id: str = "sre_agent"):
        """Lists all stored memories."""
        if self.use_openclaw_cli:
            try:
                cmd = ["openclaw", "mem0", "list", "--user-id", user_id, "--json"]
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    # The JSON format is: {"ok": true, "memories": [{"memory": "..."}]}
                    memories_list = data.get("memories", data.get("results", []))
                    if isinstance(memories_list, list):
                        return [item["memory"] for item in memories_list if "memory" in item]
                else:
                    print(f"WARNING: OpenClaw CLI list returned non-zero code {res.returncode}: {res.stderr}")
            except Exception as e:
                print(f"WARNING: OpenClaw CLI list failed: {e}. Falling back.")

        if self.use_mem0:
            results = self.memory.get_all(user_id=user_id)
            normalized = []
            for r in results:
                if isinstance(r, dict):
                    normalized.append(r.get("memory", r.get("text", r.get("memory_text", str(r)))))
                elif isinstance(r, str):
                    normalized.append(r)
            return normalized
        else:
            try:
                with open(self.fallback_db_path, "r") as f:
                    memories = json.load(f)
            except Exception:
                return []
            return [m.get("text", "") for m in memories if m.get("user_id") == user_id]
