import os
import re
from llmwiki.db.store import Store

def migrate_links(vault_path="vault"):
    store = Store(vault_path)
    pages_dir = os.path.join(vault_path, "pages")
    # Regex for [[path/to/page|Alias]] or [[page]]
    wiki_link_regex = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
    
    for root, _, files in os.walk(pages_dir):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, pages_dir)
                source = rel_path.replace(".md", "")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    links = re.findall(wiki_link_regex, content)
                    for target in links:
                        target = target.strip()
                        if '/' not in target:
                            target = f"entities/{target}"
                        store.add_link(source, target)
    print("Migration complete.")

if __name__ == "__main__":
    migrate_links()
