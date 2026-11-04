"""Workshops: separate workspaces of the app next to the building constructor. Each keeps its models in its own
folder under projects/ and has its own UI module in web/ws/<id>.js. Shared endpoints live here; each workshop
adds its own under /api/ws/<id>/..."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from ..core import blender
from .project import PROJECTS

WORKSHOPS = {
    "items": {"title": "Предметы", "dir": "items",
              "about": "Мелкие объекты и декали: посуда, еда, книги, инструменты, мелочи для интерьера."},
    "clothes": {"title": "Одежда", "dir": "clothes",
                "about": "Одежда для разных персонажей: подгонка под тело, слои, ткань."},
    "rig": {"title": "Риг и анимация", "dir": "rigs",
            "about": "Кости, веса, анимации и проверка движения: пересечения, растяжения, реалистичность."},
}
router = APIRouter(prefix="/api/ws")


@router.get("")
def workshops():
    return [{"id": k, "title": v["title"], "about": v["about"]} for k, v in WORKSHOPS.items()]


@router.get("/blender")
async def blender_info():
    return await asyncio.to_thread(blender.info)


@router.get("/{wid}/models")
def models(wid: str):
    """GLB files of a workshop (paths relative to projects/, viewable via /files/...)."""
    if wid not in WORKSHOPS:
        raise HTTPException(404, f"unknown workshop {wid}")
    d = PROJECTS / WORKSHOPS[wid]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return [{"path": p.relative_to(PROJECTS).as_posix(), "name": p.stem, "kb": round(p.stat().st_size / 1e3)}
            for p in sorted(d.rglob("*.glb"))]
