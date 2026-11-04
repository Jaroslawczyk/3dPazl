"""Transport workshop: parametric low-poly vehicles (see kit.py for how they are built, docs/model_craft.md for why).

build(kind, params) -> Kit; export_glb(kind, params, path) writes a Y-up GLB: one palette texture, wheels and rotors as
separate nodes. Params: color, color2 ('#rrggbb'), livery, text (plate, route or side number), detail 1-3, length, size, seed."""
from __future__ import annotations

import random
from pathlib import Path

from . import rail_air, road, water
from .kit import Kit

BODY_COLORS = ["#c8342c", "#2f5fa8", "#eef0f4", "#8f97ad", "#3f8f5a", "#e8b33c", "#d9673a"]
FREE_COLOR = ("sedan", "hatch", "suv", "sport", "pickup", "van", "motorcycle")


def _car(style):
    def make(k):
        road.car(k, style, road.LIVERIES.get(k.p["livery"]))
    return make


def _taxi(k):
    k.default_colors("#f8c13a", "#2b2d34")
    road.car(k, "sedan", road.taxi)


def _police(k):
    k.default_colors("#2b2d34", "#eef0f4")
    road.car(k, "sedan", road.police)


def _truck(cargo):
    def make(k):
        k.default_colors("#2f5fa8" if cargo == "box" else "#d9673a", "#eef0f4")
        road.truck(k, cargo)
    return make


def _bus(k):
    k.default_colors("#e8b33c", "#eef0f4")
    road.bus(k)


KINDS = {
    "road": {"sedan": ("Седан", _car("sedan")), "hatch": ("Хэтчбек", _car("hatch")), "suv": ("Внедорожник", _car("suv")), "sport": ("Спорткар", _car("sport")),
             "pickup": ("Пикап", _car("pickup")), "van": ("Фургон", _car("van")), "taxi": ("Такси", _taxi), "police": ("Полиция", _police),
             "bus": ("Автобус", _bus), "truck_box": ("Грузовик с кузовом", _truck("box")), "truck_tank": ("Бензовоз", _truck("tank")),
             "truck_dump": ("Самосвал", _truck("dump")), "fire_truck": ("Пожарная машина", road.fire_truck), "tractor": ("Трактор", road.tractor),
             "motorcycle": ("Мотоцикл", road.motorcycle)},
    "rail": {"locomotive": ("Паровоз", rail_air.locomotive), "tender": ("Тендер", rail_air.tender), "wagon": ("Пассажирский вагон", lambda k: rail_air.wagon(k, "passenger")),
             "wagon_box": ("Товарный вагон", lambda k: rail_air.wagon(k, "box")), "wagon_tank": ("Вагон-цистерна", lambda k: rail_air.wagon(k, "tank")),
             "wagon_logs": ("Платформа с брёвнами", lambda k: rail_air.wagon(k, "flat"))},
    "water": {"rowboat": ("Лодка", water.rowboat), "speedboat": ("Катер", water.speedboat), "sailboat": ("Яхта", water.sailboat), "fishing": ("Рыболовный баркас", water.fishing),
              "tug": ("Буксир", water.tug), "cargo_ship": ("Контейнеровоз", water.cargo_ship), "liner": ("Лайнер", water.liner), "galleon": ("Парусник", water.galleon)},
    "air": {"light_plane": ("Лёгкий самолёт", rail_air.light_plane), "airliner": ("Пассажирский самолёт", rail_air.airliner), "helicopter": ("Вертолёт", rail_air.helicopter)},
}
GROUPS = {"road": "Дорога", "rail": "Железная дорога", "water": "Вода", "air": "Воздух"}
LIVERIES = {"plain": "Однотонная", "stripe": "Полоса по борту", "racing": "Гоночные полосы", "two_tone": "Двухцветная"}
FUNCS = {k: v for g in KINDS.values() for k, v in g.items()}
DEFAULTS = {"color": "", "color2": "", "livery": "plain", "text": "", "detail": 2, "length": 1.0, "size": 1.0, "seed": 1}


def catalog():
    return {"groups": [{"id": g, "title": GROUPS[g], "kinds": [{"id": k, "title": t} for k, (t, _) in KINDS[g].items()]} for g in KINDS],
            "liveries": LIVERIES, "params": DEFAULTS}


def build(kind: str, params: dict | None = None) -> Kit:
    if kind not in FUNCS:
        raise KeyError(f"unknown vehicle kind {kind}; known: {', '.join(FUNCS)}")
    p = {**DEFAULTS, **(params or {})}
    p["detail"] = int(min(3, max(1, p["detail"])))
    p["length"] = float(min(1.5, max(0.7, p["length"])))
    R = random.Random(int(p["seed"]))
    k = Kit(p, R)
    if kind in FREE_COLOR:
        k.default_colors(R.choice(BODY_COLORS), "#eef0f4")
    FUNCS[kind][1](k)
    k.finish(float(p["size"]))
    return k


def export_glb(kind: str, params: dict | None, path: Path) -> dict:
    k = build(kind, params)
    lo, hi = k.bounds()
    return {"kind": kind, "size_m": [round(float(x), 2) for x in hi - lo], "params": k.p, **k.write(path)}
