# Long animations (dances, tricks) for characters

Use `pazl/core/rig/choreo.py`; worked example: `scripts/make_dance_headspin.py` (dance -> roll into a headstand ->
headspin -> back up, one looping clip). Check with `anim_qa(name, clip)` (MCP) or `choreo.qa`.

## How a choreography is written
- A timeline of keys `{"t": s, "pose": {bone: Rot}, "flip": deg about X (whole body; 180 = upside down), "spin": deg/s
  about the vertical, "anchor": "feet" | "head" | "hands" | "free"}`. Bones missing in a key fall back to the base pose.
- Between keys every bone is slerped with smoothstep easing; spin is integrated per frame (any number of turns, smooth).
- Root height: the lowest point of the posed body (with hat, hair, pet) is put on the floor every frame.
- Anchor: the contact (ankles / wrists / top of the head, joint positions - continuous) keeps its place on the floor,
  so feet do not slide in a dance and a headspin turns about the head.

## Conventions (our rigs)
Figure faces +Z, its left is +X. `thigh` x<0 = leg forward, `shin` x>0 = knee bends, foot x = -(thigh+shin) keeps it
flat. Arms: bind is T-pose; to hang them use the character's own `rest_pose` (all in `upper_arm`, nothing in the
shoulder - `use_rest()` in the example); then x<0 raises the arm forward/up, z opens it sideways.

## Rules learned (dance + headspin for galaxy_1to1, 2026-11-04)
| Problem the QA found | Fix |
|---|---|
| armpit gap 5-8 cm when arms move (rigid R15 blocks) | joint balls at shoulder/elbow/wrist/hip/knee/ankle in the body (rebuild script) |
| arms lowered half in the shoulder, half in the arm: arm leaves the torso | lower them exactly like the character's rest pose |
| whole body shook 30-67 cm/frame | contact from joints, not from the lowest surface point (it jumps heel/toe, foot/foot) |
| jerks on fast changes (arms up in 0.25 s, crouch in 0.45 s, unfold + spin together) | give big moves >= 0.5-0.8 s; do not start a spin while the legs unfold |
| headspin 540 deg/s = 29 cm/frame at the feet | 300 deg/s (about 1 turn in 1.2 s) reads as fast and stays smooth at 30 fps |
| false "head inside chest", "thigh inside chest" | blocks joined through bones without a block (neck, shoulder, hips) are neighbours |

## Iterate fast
`scripts/make_dance_headspin.py` rebuilds the clip + QA in seconds; `--export` writes the character GLB (slow, it is
repaired too); `--check-only` re-runs the QA. Look at it in the app: «Персонажи» -> the character -> clip, or load the
GLB and play it with an AnimationMixer.
