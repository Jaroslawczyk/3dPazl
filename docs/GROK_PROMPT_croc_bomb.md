# Промпт для Grok: текстуры к аватару `croc_bomb` (майка с крокодилом + бомба с фитилём)

Модель уже собрана: `projects/chars/croc_bomb.glb`, выгрузка для Roblox: `projects/roblox/croc_bomb/`.
Проверка сетки (`mesh_check`): дыр, прорезов тела, плавающих частей нет. Принт на майке стоит строго внутри передней грани торса
(x ±0.164 м при ширине грани ±0.28, y 0.83-1.16 при грани 0.75-1.22) — за края не выходит.

## Куда класть результат
| Файл | Куда | Что |
|---|---|---|
| `croc_tank.png` | `projects/skins/prints/croc_tank.png` (заменить заглушку) | принт крокодила на груди |
| `croc_tank_normal.png`, `croc_tank_height.png`, `croc_tank_ao.png`, `croc_tank_rough.png` | `projects/skins/prints/` | карты к принту |
| `bomb_albedo.png`, `bomb_normal.png`, `bomb_height.png`, `bomb_rough.png`, `bomb_ao.png` | `projects/skins/` | тайловый материал корпуса бомбы |

Потом скажи мне «текстуры готовы» — я подставлю и пересоберу.

## Общие требования (вставь в начало каждого запроса)
```
Stylized game texture for a Roblox avatar, clean hand-painted PBR look, soft cartoon style with bold readable shapes,
slightly glossy toy-like finish, saturated colours, thick dark-green/black outline (3-4 px at 1024), no photorealism,
no text, no watermark, no logo, no border, flat orthographic view straight from the front, no perspective, no lighting
baked into the colour map (NO cast shadows, NO highlights in the albedo - shading comes from separate maps).
Square 1024x1024 PNG, 8 bit, sRGB. Output ONLY the requested map, nothing else in the frame.
```

## 1. Принт крокодила на майке (albedo, с прозрачным фоном)
```
[general requirements above]
Chest print for a white tank top: a cute cartoon crocodile face (front view, mouth slightly open with a few
rounded teeth, two big round eyes with white highlights, two nostrils), green body colours #3fa34d / #2b7d3a with
a lighter belly-cream #e8e2a8 muzzle, orange tongue. Centred, fills 90% of the canvas, rounded silhouette,
the whole picture fits inside a circle so nothing touches the image edge. TRANSPARENT background (PNG alpha).
Size 1024x1024.
```
Карты к нему — по одной, тот же рисунок, тот же размер и те же координаты, фон чёрный/нейтральный:
```
Same crocodile print, same composition and exact same pixel positions, as a TANGENT-SPACE NORMAL MAP (OpenGL, +Y up,
green = up, like glTF). Scaly skin bumps on the body, raised outline, soft bump on the eyes and teeth. Flat areas = #8080FF.
```
```
Same crocodile print, same pixel positions, as a 16-bit-style grayscale HEIGHT map: black = lowest, white = highest.
Scales and teeth raised, eye sockets sunk, outline slightly raised. Smooth gradients, no noise on flat parts.
```
```
Same crocodile print, same pixel positions, as a grayscale AMBIENT OCCLUSION map (white = open, dark = crevice):
darken only between scales, around the eyes, inside the mouth and under the teeth.
```
```
Same crocodile print, same pixel positions, as a grayscale ROUGHNESS map: skin 0.55 (mid-grey), eyes 0.15 (dark),
teeth 0.3, tongue 0.4.
```

## 2. Бомба на голове — корпус (бесшовный материал)
Корпус — шар, цвет сейчас задан вершинами (#25252b), текстура подмешивается как тайловый скин.
```
[general requirements above, but SEAMLESS / TILEABLE in both directions, no visible repeat]
Cartoon black bomb shell material: matte-glossy dark charcoal metal #25252b with slight blue tint, subtle hand-painted
wear, tiny light-grey scratches and a few rivet-like dots in a regular grid, no big shapes, no logos. Albedo map.
```
Карты (те же требования, бесшовные, тот же узор по пикселям): `normal` (OpenGL, #8080FF плоское — вмятины, царапины, заклёпки),
`height` (серая, заклёпки выше, царапины ниже), `roughness` (серая 0.35-0.6, царапины светлее), `ao` (светлая, тёмное только в щелях).

## 3. Фитиль и искра (необязательно)
Сейчас вершинными цветами: верёвка #c9a56a, искра #ff8a1f/#ffd84a, воротник металл #6b6b73. Если хочешь текстуру:
```
[general requirements above, SEAMLESS horizontally] Twisted rope fuse material, 1024x256, warm beige #c9a56a with darker
diagonal twist lines, slightly frayed look. Albedo, then matching normal / height / roughness maps.
```

## Про «все тени»
Тени и объём должны идти из normal / height / AO, а не быть нарисованы в цвете: в игре Roblox свет и тени считает движок,
а запечённая в альбедо тень будет двоиться и грязнить цвет. Если нужен «запечённый» вариант для превью — отдельным файлом
`*_baked.png`.
