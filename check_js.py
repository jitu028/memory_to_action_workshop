import re

js_path = "/Users/jitendragupta/.openclaw/npm/projects/mem0-openclaw-mem0-09729737ad/node_modules/@mem0/openclaw-mem0/dist/index.js"

with open(js_path, "r", encoding="utf-8") as f:
    content = f.read()

# Look for ".command(" or "command("
for match in re.finditer(r'command\s*\(\s*["\'`][^"\'`]*import[^"\'`]*["\'`]', content):
    pos = match.start()
    print(f"Match found at position {pos}:")
    print(content[pos-100:pos+1000])
    print("="*80)
