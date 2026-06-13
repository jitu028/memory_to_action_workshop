import os
import json
import re
from datetime import datetime, timedelta

workspace_dir = "/Users/jitendragupta/.openclaw/workspace"
import_file_path = "/tmp/mem0_import.json"

# Step 4: Files from workspace
target_files = ["SOUL.md", "IDENTITY.md", "USER.md", "MEMORY.md"]
found_files = []
imported_items = []

for filename in target_files:
    path = os.path.join(workspace_dir, filename)
    if os.path.exists(path):
        found_files.append(os.path.relpath(path, workspace_dir))
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Count words (simple space split)
        words = content.split()
        if len(words) < 2000:
            imported_items.append({"text": f"File: {filename}\n\n{content}"})
        else:
            # Split by headings
            # Split by lines and group by heading
            chunks = []
            current_chunk = []
            for line in content.split("\n"):
                if line.startswith("#"):
                    if current_chunk:
                        chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                else:
                    current_chunk.append(line)
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                
            for chunk in chunks:
                if chunk.strip():
                    imported_items.append({"text": f"File: {filename}\n\n{chunk}"})

# Step 5: Memory folder YYYY-MM-DD.md (most recent 30 days)
memory_dir = os.path.join(workspace_dir, "memory")
if os.path.exists(memory_dir):
    print("Memory directory exists. Scanning YYYY-MM-DD.md files...")
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    
    for file in os.listdir(memory_dir):
        if file.endswith(".md"):
            # Check YYYY-MM-DD format
            match = re.match(r'^(\d{4}-\d{2}-\d{2})\.md$', file)
            if match:
                date_str = match.group(1)
                try:
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if file_date >= thirty_days_ago:
                        path = os.path.join(memory_dir, file)
                        found_files.append(os.path.relpath(path, workspace_dir))
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        words = content.split()
                        if len(words) < 2000:
                            imported_items.append({"text": f"Date: {date_str}\n\n{content}"})
                        else:
                            # Split by headings
                            chunks = []
                            current_chunk = []
                            for line in content.split("\n"):
                                if line.startswith("#"):
                                    if current_chunk:
                                        chunks.append("\n".join(current_chunk))
                                    current_chunk = [line]
                                else:
                                    current_chunk.append(line)
                            if current_chunk:
                                chunks.append("\n".join(current_chunk))
                                
                            for chunk in chunks:
                                if chunk.strip():
                                    imported_items.append({"text": f"Date: {date_str}\n\n{chunk}"})
                except ValueError:
                    # Invalid date format in name
                    continue
else:
    print("Memory directory does not exist. Skipping.")

# Step 6: Write to /tmp/mem0_import.json
print(f"Found files to import: {found_files}")
print(f"Total items created: {len(imported_items)}")

with open(import_file_path, "w", encoding="utf-8") as f:
    json.dump(imported_items, f, indent=2)

print(f"Successfully wrote import file to {import_file_path}")
