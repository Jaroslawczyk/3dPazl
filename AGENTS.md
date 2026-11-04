# 3dPazl for AI agents

**Read [docs/QUICKSTART.md](docs/QUICKSTART.md) first**: file map, how to view results in the app, budgets, the user's rules.

Use the `pazl` MCP server (`.mcp.json`, `.cursor/mcp.json`; Codex: `[mcp_servers.pazl]` in `~/.codex/config.toml`). Start by reading its `guide` tool.

**Never drive 3dPazl through its own «ИИ» chat tab or by clicking the UI to build.** That tab starts a second AI (Codex/Claude/Gemini) that re-reads everything, so tokens are paid twice and every screenshot costs more than a tool reply. Build with the MCP tools or the Python API (`docs/QUICKSTART.md`); open the browser only at the end to show the result. If the `pazl` tools are missing in your session, say so to the user instead of falling back to the UI.

- Screenshots of the app for yourself: use the `view_screenshot` MCP tool (the 3D view only, no interface). If you drive a browser, open the app with `?clean=1` (F10 toggles it).
- After building or changing a model, run `mesh_check` (MCP) / `scripts/mesh_check.py`; run `mesh_fix` for what it can repair, fix the rest by hand, and only then show it to the user.
- Buildings, items, rigs: [docs/AI_GUIDE.md](docs/AI_GUIDE.md)
- Vehicles and how to build good low-poly models: [docs/model_craft.md](docs/model_craft.md)
- Characters, clothes, downloading textures from the internet, Roblox export: [docs/ROBLOX.md](docs/ROBLOX.md)

Always show results in the app. Download textures only through `skin_search` and `skin_download` (CC0 sources).
