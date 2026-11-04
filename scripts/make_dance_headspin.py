"""Dance -> drop into a headstand -> breakdance headspin -> back up, as ONE smooth looping clip for a block (R15-like)
character. Built with pazl/core/rig/choreo.py (key poses + eased transitions + whole-body flip/spin + automatic ground
contact) and checked with choreo.qa (gaps at joints, ground, pass-through, jerks).

    .venv/Scripts/python.exe scripts/make_dance_headspin.py [char] [--check-only]

Conventions (our rigs): the figure faces +Z, its left is +X. thigh x<0 = leg forward, shin x>0 = knee bends,
upper_arm needs DOWN to hang (bind is T-pose), x<0 then raises the arm forward/up."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pazl.core import chars, rig  # noqa: E402
from pazl.core.rig import choreo  # noqa: E402

q = choreo.q
CHAR = next((a for a in sys.argv[1:] if not a.startswith("--")), "galaxy_1to1")
CLIP = "dance_headspin"
BEAT = .5  # 120 BPM
DOWN = {".L": q("z", -60), ".R": q("z", 60)}
SH = {"shoulder.L": q("z", -15), "shoulder.R": q("z", 15)}


def use_rest(c):
    """Lower the arms exactly like the character's own default pose (all in the upper arm, nothing in the shoulder):
    splitting it between shoulder and arm moves the arm off the torso (a gap at the armpit)."""
    global DOWN, SH
    from scipy.spatial.transform import Rotation as Rot
    rp = c.get("rest_pose") or {}
    if "upper_arm.L" in rp and "upper_arm.R" in rp:
        DOWN = {".L": Rot.from_quat(rp["upper_arm.L"]), ".R": Rot.from_quat(rp["upper_arm.R"])}
        SH = {}


def arm(sd, x=0, z=0, fore=0, down=True):
    k = 1 if sd == ".L" else -1
    r = {"upper_arm" + sd: q("x", x) * q("z", k * z) * (DOWN[sd] if down else choreo.IDENT), "forearm" + sd: q("y", -k * fore)}
    return r


def legs(t=0, sh=0, foot=None, sd=None, spread=0):
    out = {}
    for s, k in ((".L", 1), (".R", -1)):
        if sd and s != sd:
            continue
        out.update({"thigh" + s: q("x", t) * q("z", k * spread), "shin" + s: q("x", sh), "foot" + s: q("x", -(t + sh) if foot is None else foot)})
    return out


def merge(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


def timeline():
    K = []
    stand = merge(SH, arm(".L"), arm(".R"), legs())
    K.append({"t": 0, "pose": stand})
    # 1) groove: bounce on every beat, arms pump in turn, hips sway (beats 1-4)
    for i in range(1, 5):
        L = i % 2
        side = 1 if L else -1
        K.append({"t": i * BEAT, "pose": merge(SH, legs(-14, 28), {"hips": q("y", 12 * side), "chest": q("y", -8 * side), "head": q("z", 6 * side)},
                                                  arm(".L", -75 if L else -20, 8, 70 if L else 20), arm(".R", -20 if L else -75, 8, 20 if L else 70))})
        K.append({"t": i * BEAT + BEAT * .5, "pose": merge(SH, legs(-4, 8), arm(".L", -45, 8, 45), arm(".R", -45, 8, 45))})
    # 2) side steps: one leg out, arms open (beats 5-8)
    for i in range(5, 9):
        L = i % 2
        sd = ".L" if L else ".R"
        other = ".R" if L else ".L"
        k = 1 if L else -1
        K.append({"t": i * BEAT, "pose": merge(SH, legs(-6, 12, sd=other), legs(-10, 20, spread=22, sd=sd), {"hips": q("z", -6 * k), "chest": q("z", 8 * k), "head": q("z", -6 * k)},
                                                  arm(".L", -10, 35, 25), arm(".R", -10, 35, 25))})
        if i < 8:  # no half-beat key before the arms go up: they get a whole beat to rise (no jerk)
            K.append({"t": i * BEAT + BEAT * .5, "pose": merge(SH, legs(-4, 8), arm(".L", -20, 20, 30), arm(".R", -20, 20, 30))})
    # 3) arms overhead, wave with the hips (beats 9-12)
    for i in range(9, 13):
        k = 1 if i % 2 else -1
        K.append({"t": i * BEAT, "pose": merge(SH, legs(-12, 24), {"hips": q("z", 8 * k), "chest": q("z", -6 * k), "head": q("x", -10)},
                                                  arm(".L", -150, 18 - 6 * k, 15), arm(".R", -150, 18 + 6 * k, 15))})
    t = 12 * BEAT  # 6.0 s
    # 4) drop: deep crouch, hands to the floor in front, then roll forward onto the head (flip 0 -> 180)
    crouch = merge(SH, legs(-95, 125), {"spine": q("x", 25), "chest": q("x", 30), "head": q("x", 20)}, arm(".L", -70, 10, 20), arm(".R", -70, 10, 20))
    K.append({"t": t + .7, "pose": crouch})
    tuck = merge(SH, legs(-105, 105), {"spine": q("x", 20), "chest": q("x", 25), "head": q("x", 10)}, arm(".L", -80, 25, 60), arm(".R", -80, 25, 60))
    K.append({"t": t + 1.3, "pose": tuck, "flip": 90})
    K.append({"t": t + 1.9, "pose": merge(tuck, {"head": q("x", 0)}), "flip": 180, "anchor": "head"})
    # 5) headspin: legs open up into a V, arms out for balance, spin speeds up, legs scissor, slows down
    spin_pose = merge(SH, legs(0, 0, 0, spread=28), {"spine": q("x", 0), "chest": q("x", 0)}, arm(".L", 0, 0, 10, down=False), arm(".R", 0, 0, 10, down=False))
    K.append({"t": t + 2.7, "pose": spin_pose, "flip": 180, "anchor": "head", "spin": 300})
    K.append({"t": t + 3.6, "pose": merge(spin_pose, legs(-20, 0, 0, spread=34, sd=".L"), legs(20, 0, 0, spread=34, sd=".R")), "flip": 180, "anchor": "head", "spin": 300})
    K.append({"t": t + 4.4, "pose": merge(spin_pose, legs(20, 0, 0, spread=34, sd=".L"), legs(-20, 0, 0, spread=34, sd=".R")), "flip": 180, "anchor": "head", "spin": 300})
    K.append({"t": t + 5.2, "pose": spin_pose, "flip": 180, "anchor": "head", "spin": 300})
    K.append({"t": t + 5.9, "pose": merge(tuck, {"head": q("x", 0)}), "flip": 180, "anchor": "head", "spin": 0})
    # 6) come down: roll back to the crouch, stand up, end in the first pose (the clip loops)
    K.append({"t": t + 6.6, "pose": tuck, "flip": 90, "anchor": "feet"})
    K.append({"t": t + 7.2, "pose": crouch, "flip": 0, "anchor": "feet"})
    K.append({"t": t + 8.2, "pose": stand, "flip": 0, "anchor": "feet"})
    return K


def main():
    """--check-only: QA of the saved clip; --export: also write the character GLB (slow: it is repaired too)."""
    r = rig.load(chars._rn(CHAR))
    use_rest(chars.load(CHAR))
    pts = choreo.body_points(CHAR)
    if "--check-only" not in sys.argv:
        clip = choreo.make_clip(pts, r["bones"], timeline(), fps=30, name=CLIP, loop=True)
        r["clips"][CLIP] = clip
        rig.save(r)
    if "--export" in sys.argv:
        res = chars.export(CHAR)
        print("exported", res["path"], res["tris"], "tris, clips", res["clips"])
    clip = rig.load(chars._rn(CHAR))["clips"][CLIP]
    print(choreo.qa(pts, r["bones"], clip)["text"])


if __name__ == "__main__":
    main()
