"""Rebuild the forest deer through 3dPazl's MCP character importer.

Run from the repository root while the 3dPazl app server is available:
    .venv/Scripts/python.exe scripts/rebuild_forest_deer.py
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "projects" / "refs" / "forest_deer" / "source" / "scene.gltf"
OUTPUT = ROOT / "projects" / "лесной_олень" / "export" / "лесной_олень.glb"
HEIGHT = 2.16


async def rebuild() -> None:
    os.chdir(ROOT)
    params = StdioServerParameters(
        command=str(ROOT / ".venv" / "Scripts" / "python.exe"),
        args=["-m", "pazl.mcp"],
        env={"PAZL_AGENT": "codex"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "char_import",
                {
                    "path": str(SOURCE),
                    "name": "forest_deer_1to1",
                    "height": HEIGHT,
                    "up": "auto",
                    "turn": 180,
                    "template": "humanoid",
                    "quality": "high",
                },
            )
            if result.is_error:
                details = " ".join(c.text for c in result.content if getattr(c, "text", None))
                raise RuntimeError("3dPazl char_import failed: " + details)
            response = next(c.text for c in result.content if getattr(c, "text", None))
            imported = json.loads(response)

    generated = ROOT / "projects" / imported["path"]
    if not generated.is_file():
        raise FileNotFoundError(f"3dPazl reported a missing output: {generated}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(generated, OUTPUT)
    print(f"Wrote {OUTPUT}: {imported['tris']:,} triangles, height {HEIGHT:.2f} m")


if __name__ == "__main__":
    asyncio.run(rebuild())
