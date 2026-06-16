# plugin-forge

Lint + scaffold Claude Code plugins against a house grammar. A companion in the
agentic-sop-to-work suite — but runs standalone on any plugin.

```bash
python3 plugins/plugin-forge/pluginforge/lint.py --all --strict   # lint the marketplace
python3 plugins/plugin-forge/pluginforge/lint.py <plugin-dir>     # lint one plugin
python3 plugins/plugin-forge/pluginforge/scaffold.py <name>       # generate a new plugin
```
