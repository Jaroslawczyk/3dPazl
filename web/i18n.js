// UI language: the interface is written in Russian; this table gives English and Polish. It is applied to the page
// (text, title, placeholder), to everything added later, and to prompt/confirm dialogs. AI chat text is left as is.
export const LANGS = { ru: 'Русский', en: 'English', pl: 'Polski' };
let lang = 'ru';
try { lang = localStorage.getItem('pazl.lang') || 'ru'; } catch { /* private mode: Russian */ }
if (!LANGS[lang]) lang = 'ru';
export const LANG = lang;

const D = [
  // header
  ['О программе', 'About', 'O programie'], ['Название проекта', 'Project name', 'Nazwa projektu'],
  ['Новый проект', 'New project', 'Nowy projekt'], ['Открыть сохранённый проект', 'Open a saved project', 'Otwórz zapisany projekt'],
  ['Отменить (Ctrl+Z)', 'Undo (Ctrl+Z)', 'Cofnij (Ctrl+Z)'], ['Повторить (Ctrl+Y)', 'Redo (Ctrl+Y)', 'Ponów (Ctrl+Y)'],
  ['Смешать со вторым стилем (первый главный: материалы и пропорции, второй дополняет)', 'Mix with a second style (the first one leads: materials and proportions; the second fills in)', 'Połącz z drugim stylem (pierwszy prowadzi: materiały i proporcje, drugi uzupełnia)'],
  ['Реализм — с PBR-текстурами; Low-poly — без текстур, плоские цвета', 'Realistic — PBR textures; Low-poly — flat colours, no textures', 'Realizm — tekstury PBR; Low-poly — płaskie kolory bez tekstur'],
  ['Случайно покрасить фасады по палитре стиля', 'Paint facades randomly from the style palette', 'Losowo pomaluj fasady z palety stylu'],
  ['Перебросить случайности (этажи-диапазоны, миксы, декали)', 'Re-roll random values (floor ranges, mixes, decals)', 'Wylosuj ponownie (zakresy pięter, miksy, naklejki)'],
  ['Сгенерировать интерьер: комнаты, лестницы, лифты, мебель', 'Generate interiors: rooms, stairs, lifts, furniture', 'Wygeneruj wnętrza: pokoje, schody, windy, meble'],
  ['Состарить: грязь, подтёки, мох, граффити', 'Weather it: dirt, streaks, moss, graffiti', 'Postarz: brud, zacieki, mech, graffiti'],
  ['Какие места в сетках окон — окна, а какие заложены кладкой, закрыты ставнями или досками', 'Which slots of window grids are windows and which are bricked up, shuttered or boarded', 'Które miejsca w siatkach okien są oknami, a które zamurowane, zamknięte okiennicami lub deskami'],
  ['Формы зданий: не только прямоугольники', 'Building shapes: not only rectangles', 'Kształty budynków: nie tylko prostokąty'],
  ['Проверить цельность: щели, висящие части, ошибки', 'Check integrity: gaps, floating parts, errors', 'Sprawdź spójność: szczeliny, wiszące części, błędy'],
  ['Скриншоты со всех 12 сторон одним листом', 'Screenshots from all sides on one sheet', 'Zrzuty ze wszystkich stron na jednym arkuszu'],
  ['Текстуры', 'Textures', 'Tekstury'], ['Экспорт цельной модели', 'Export the model', 'Eksport modelu'],
  ['Эпохи', 'Periods', 'Epoki'], ['Территория', 'Region', 'Region'], ['Поиск: окно, купол, колонна…', 'Search: window, dome, column…', 'Szukaj: okno, kopuła, kolumna…'],
  ['Выбор (Q)', 'Select (Q)', 'Wybór (Q)'], ['Двигать (W)', 'Move (W)', 'Przesuń (W)'], ['Вращать вокруг вертикали (E)', 'Rotate around the vertical (E)', 'Obróć wokół pionu (E)'],
  ['Пометки для ИИ: клик — точка, протянуть — нарисовать. Вращать камеру — правой кнопкой', 'Marks for the AI: click = point, drag = draw. Rotate the camera with the right button', 'Znaczniki dla AI: klik = punkt, przeciągnij = rysuj. Kamera — prawym przyciskiem'],
  ['Вид спереди', 'Front view', 'Widok z przodu'], ['Вид сбоку', 'Side view', 'Widok z boku'], ['Вид сверху', 'Top view', 'Widok z góry'], ['Изометрия', 'Isometric', 'Izometria'],
  ['Показывать сварную (итоговую) модель вместо разборной', 'Show the welded (final) model instead of the parts', 'Pokaż zespawany (końcowy) model zamiast części'],
  ['Камера повторяет ракурсы, с которых ИИ проверяет модель', 'The camera follows the views the AI checks', 'Kamera powtarza widoki, które sprawdza AI'],
  ['Настоящий интерьер внутри здания: комнаты, перегородки, лестницы, мебель', 'Real interior: rooms, partitions, stairs, furniture', 'Prawdziwe wnętrze: pokoje, ścianki, schody, meble'],
  ['Окна: прозрачное стекло (видно, что внутри) или визуальная затычка — картинка комнаты за стеклом', 'Windows: clear glass (you see inside) or a visual plug — a room picture behind the glass', 'Okna: przezroczyste szkło (widać wnętrze) lub zaślepka — obraz pokoju za szybą'],
  ['3D-иллюзия глубины комнат (interior mapping) вместо плоской картинки', '3D illusion of room depth (interior mapping) instead of a flat picture', 'Iluzja głębi pokoju (interior mapping) zamiast płaskiego obrazu'],
  ['Срез по высоте, чтобы заглянуть внутрь', 'Height cut to look inside', 'Przekrój wysokości, by zajrzeć do środka'],
  ['Какой ИИ', 'Which AI', 'Które AI'], ['модель', 'model', 'model'], ['Модель', 'Model', 'Model'],
  ['Адрес OpenAI-совместимого API', 'OpenAI-compatible API address', 'Adres API zgodnego z OpenAI'], ['API-ключ', 'API key', 'Klucz API'],
  ['Хранится только на этом компьютере', 'Stored only on this computer', 'Przechowywany tylko na tym komputerze'],
  ['Глубина размышлений (Claude)', 'Thinking depth (Claude)', 'Głębokość myślenia (Claude)'],
  ['Отправлять модели скриншоты (нужна модель с поддержкой изображений)', 'Send screenshots to the model (needs a vision model)', 'Wysyłaj zrzuty do modelu (wymaga modelu z obsługą obrazów)'],
  ['Открыть вход в аккаунт (откроется окно и браузер)', 'Sign in to the account (opens a window and the browser)', 'Zaloguj się (otworzy się okno i przeglądarka)'],
  ['Установить программу через npm (нужен Node.js)', 'Install the program with npm (needs Node.js)', 'Zainstaluj program przez npm (wymaga Node.js)'],
  ['Начать новый разговор', 'Start a new conversation', 'Nowa rozmowa'],
  ['ИИ поменяет только отмеченные элементы, остальное заблокировано', 'The AI changes only the marked elements; everything else is locked', 'AI zmieni tylko zaznaczone elementy; reszta jest zablokowana'],
  ['Например: построй деревянную церковь с тремя куполами (Enter — отправить, Shift+Enter — новая строка)', 'E.g.: build a wooden church with three domes (Enter = send, Shift+Enter = new line)', 'Np.: zbuduj drewniany kościół z trzema kopułami (Enter = wyślij, Shift+Enter = nowa linia)'],
  ['3dPazl — конструктор зданий', '3dPazl — building constructor', '3dPazl — konstruktor budynków'],
  ['Новый', 'New', 'Nowy'], ['Открыть…', 'Open…', 'Otwórz…'], ['Стиль', 'Style', 'Styl'], ['Реализм', 'Realistic', 'Realizm'],
  ['🎲 Покрасить', '🎲 Paint', '🎲 Pomaluj'], ['🎲 Сид', '🎲 Seed', '🎲 Ziarno'], ['🏠 Интерьер', '🏠 Interior', '🏠 Wnętrze'], ['🧱 Состарить', '🧱 Weather', '🧱 Postarz'],
  ['🪟 Окна…', '🪟 Windows…', '🪟 Okna…'], ['Все окна', 'All windows', 'Wszystkie okna'], ['Случайно: часть заложена', 'Random: some bricked up', 'Losowo: część zamurowana'],
  ['Случайно, но симметрично', 'Random but symmetric', 'Losowo, ale symetrycznie'], ['Шахматка', 'Checkerboard', 'Szachownica'], ['Через одно', 'Every other', 'Co drugie'],
  ['По формуле…', 'By formula…', 'Według wzoru…'], ['🏛 Формы…', '🏛 Shapes…', '🏛 Kształty…'], ['🎲 Разные (случайно)', '🎲 Varied (random)', '🎲 Różne (losowo)'],
  ['Прямоугольные', 'Rectangular', 'Prostokątne'], ['Круглые', 'Round', 'Okrągłe'], ['Овальные', 'Oval', 'Owalne'], ['Закруглённые углы', 'Rounded corners', 'Zaokrąglone narożniki'],
  ['Г-образные', 'L-shaped', 'W kształcie L'], ['П-образные', 'U-shaped', 'W kształcie U'], ['Т-образные', 'T-shaped', 'W kształcie T'], ['Восьмиугольные', 'Octagonal', 'Ośmiokątne'],
  ['Трапеция', 'Trapezoid', 'Trapez'], ['Клин (утюг)', 'Wedge (flatiron)', 'Klin (żelazko)'], ['Выпуклый фасад', 'Bow front', 'Wypukła fasada'], ['Срезанный угол', 'Cut corner', 'Ścięty narożnik'], ['Крест', 'Cross', 'Krzyż'],
  ['✓ Проверить', '✓ Check', '✓ Sprawdź'], ['📷 Со всех сторон', '📷 All sides', '📷 Ze wszystkich stron'], ['🎨 Текстуры…', '🎨 Textures…', '🎨 Tekstury…'],
  ['Скачать PBR для проекта (CC0)', 'Download PBR for the project (CC0)', 'Pobierz PBR dla projektu (CC0)'], ['Скачать все паки (~70 × 8 МБ)', 'Download all packs (~70 × 8 MB)', 'Pobierz wszystkie paczki (~70 × 8 MB)'],
  ['Промпты для ИИ-генерации', 'Prompts for AI texture generation', 'Prompty do generowania przez AI'], ['Экспорт…', 'Export…', 'Eksport…'],
  ['GLB (игры, Unity/Unreal/Godot)', 'GLB (games, Unity/Unreal/Godot)', 'GLB (gry, Unity/Unreal/Godot)'], ['STL (цельный меш)', 'STL (single mesh)', 'STL (jedna siatka)'],
  ['GLB LOD (меньше треугольников)', 'GLB LOD (fewer triangles)', 'GLB LOD (mniej trójkątów)'],
  ['Здание', 'Building', 'Budynek'], ['Библиотека', 'Library', 'Biblioteka'], ['Стили', 'Styles', 'Style'], ['Материалы', 'Materials', 'Materiały'],
  ['Клик — выбрать. Элементы вложены по тому, к чему прикреплены.', 'Click to select. Elements are nested by what they are attached to.', 'Kliknij, aby wybrać. Elementy są zagnieżdżone według mocowania.'],
  ['Все территории', 'All regions', 'Wszystkie regiony'], ['Текстуры (выкл. — плоские цвета)', 'Textures (off = flat colours)', 'Tekstury (wył. = płaskie kolory)'],
  ['Декали', 'Decals', 'Naklejki'], ['Текстуры материалов', 'Material textures', 'Tekstury materiałów'],
  ['Замените текстуру любого материала модели на другую или уберите её.', "Replace any material's texture with another one or remove it.", 'Zamień teksturę dowolnego materiału na inną lub ją usuń.'],
  ['✎ Пометки', '✎ Marks', '✎ Znaczniki'], ['Перед', 'Front', 'Przód'], ['Бок', 'Side', 'Bok'], ['Верх', 'Top', 'Góra'], ['Цельная', 'Welded', 'Spawany'], ['Каркас', 'Wireframe', 'Siatka'],
  ['Камера ИИ', 'AI camera', 'Kamera AI'], ['Интерьер', 'Interior', 'Wnętrze'], ['Окна прозрачные', 'Clear windows', 'Przezroczyste okna'], ['Затычка', 'Plug', 'Zaślepka'],
  ['3D-иллюзия', '3D illusion', 'Iluzja 3D'], ['Срез', 'Cut', 'Przekrój'], ['сборка…', 'building…', 'budowanie…'], ['Свойства', 'Properties', 'Właściwości'],
  ['Выберите элемент в сцене или в дереве.', 'Select an element in the scene or in the tree.', 'Wybierz element w scenie lub w drzewie.'],
  ['💬 Чат с ИИ', '💬 AI chat', '💬 Czat z AI'], ['Лента работы ИИ', 'AI activity', 'Aktywność AI'], ['Проверка', 'Check', 'Kontrola'], ['Скриншоты', 'Screenshots', 'Zrzuty'],
  ['Напишите, что построить или изменить. ИИ работает теми же инструментами, что и через MCP.', 'Write what to build or change. The AI uses the same tools as over MCP.', 'Napisz, co zbudować lub zmienić. AI używa tych samych narzędzi co przez MCP.'],
  ['быстро', 'fast', 'szybko'], ['средне', 'medium', 'średnio'], ['тщательно', 'thorough', 'dokładnie'], ['очень тщательно', 'very thorough', 'bardzo dokładnie'],
  ['картинки', 'images', 'obrazy'], ['Войти', 'Sign in', 'Zaloguj'], ['Установить', 'Install', 'Zainstaluj'], ['Новый чат', 'New chat', 'Nowy czat'],
  ['▶ ИИ: переделать отмеченное', '▶ AI: redo the marked places', '▶ AI: popraw zaznaczone'], ['Очистить пометки', 'Clear marks', 'Wyczyść znaczniki'],
  ['Текст ниже — общая задача (необязательно).', 'The text below is the overall task (optional).', 'Tekst poniżej to zadanie ogólne (opcjonalnie).'],
  ['Отправить', 'Send', 'Wyślij'], ['Стоп', 'Stop', 'Stop'], ['Нажмите «Проверить».', 'Press “Check”.', 'Naciśnij „Sprawdź”.'],
  ['Конструктор цельных 3D-зданий.', 'Constructor of watertight 3D buildings.', 'Konstruktor szczelnych budynków 3D.'], ['Автор:', 'Author:', 'Autor:'],
  ['© 2026 Yaraslau Sychou. Все права защищены.', '© 2026 Yaraslau Sychou. All rights reserved.', '© 2026 Yaraslau Sychou. Wszelkie prawa zastrzeżone.'], ['Лицензия:', 'License:', 'Licencja:'],
  ['бесплатно только для некоммерческого использования (личное, хобби, обучение).', 'free for non-commercial use only (personal, hobby, education).', 'bezpłatnie tylko do użytku niekomercyjnego (osobisty, hobby, nauka).'],
  ['Любое коммерческое использование — только по письменному договору с автором.', 'Any commercial use only under a written agreement with the author.', 'Każde użycie komercyjne tylko na podstawie pisemnej umowy z autorem.'],
  ['Полный текст лицензии', 'Full license text', 'Pełny tekst licencji'],
  ['Сторонние компоненты (three.js, библиотеки Python, текстуры CC0) — под своими лицензиями, см. THIRD_PARTY_NOTICES.txt.', 'Third-party components (three.js, Python libraries, CC0 textures) keep their own licenses, see THIRD_PARTY_NOTICES.txt.', 'Komponenty zewnętrzne (three.js, biblioteki Python, tekstury CC0) mają własne licencje, zob. THIRD_PARTY_NOTICES.txt.'],
  ['Закрыть', 'Close', 'Zamknij'],
  // status, props, library
  ['элементов', 'elements', 'elementów'], ['треугольников', 'triangles', 'trójkątów'], ['разборный режим', 'parts mode', 'tryb części'], ['цельная сварная модель', 'welded model', 'spawany model'],
  ['📷 ИИ проверяет вид:', '📷 AI checks view:', '📷 AI sprawdza widok:'], ['поворот', 'rotation', 'obrót'], ['ручное перемещение', 'manual move', 'ręczne przesunięcie'],
  ['число', 'number', 'liczba'], ['диапазон', 'range', 'zakres'], ['микс', 'mix', 'miks'],
  ['Выберите элемент в сцене или в дереве. Режимы: Q — выбор, W — двигать, E — вращать.', 'Select an element in the scene or in the tree. Modes: Q select, W move, E rotate.', 'Wybierz element w scenie lub drzewie. Tryby: Q wybór, W przesuń, E obróć.'],
  ['Положение', 'Placement', 'Położenie'], ['к чему прикреплён: id:якорь', 'attached to: id:anchor', 'przymocowany do: id:kotwica'],
  ['[u,v] на фасаде или [x,y] на крыше, можно "50%"', '[u,v] on a facade or [x,y] on a roof, "50%" allowed', '[u,v] na fasadzie lub [x,y] na dachu, można "50%"'],
  ['доп. смещение [x,y,z] в системе якоря', 'extra offset [x,y,z] in the anchor frame', 'dodatkowe przesunięcie [x,y,z] w układzie kotwicy'],
  ['поворот вокруг вертикали, °', 'rotation around the vertical, °', 'obrót wokół pionu, °'],
  ['свой стиль элемента, можно микс: "gothic+baroque"', 'own style of the element, mixes allowed: "gothic+baroque"', 'własny styl elementu, można miks: "gothic+baroque"'],
  ['Параметры', 'Parameters', 'Parametry'], ['Применить', 'Apply', 'Zastosuj'], ['Дублировать', 'Duplicate', 'Duplikuj'], ['Удалить', 'Delete', 'Usuń'], ['Якоря', 'Anchors', 'Kotwice'],
  ['правка параметров', 'parameter edit', 'edycja parametrów'], ['удалён', 'deleted', 'usunięto'], ['копия', 'copy', 'kopia'], ['разобран макрос', 'macro exploded', 'makro rozłożone'],
  ['Якоря (к ним можно крепить элементы):', 'Anchors (elements can be attached to them):', 'Kotwice (można do nich mocować elementy):'],
  ['Фасад: окна на стороне', 'Facade: windows on a side', 'Fasada: okna na stronie'], ['сторона', 'side', 'strona'], ['все стороны', 'all sides', 'wszystkie strony'],
  ['окна', 'windows', 'okna'], ['без окон', 'no windows', 'bez okien'], ['наличник', 'surround', 'opaska'], ['ширина × высота', 'width × height', 'szerokość × wysokość'],
  ['Заменить окна', 'Replace windows', 'Zamień okna'], ['стены', 'walls', 'ściany'], ['крыша', 'roof', 'dach'], ['декор', 'decor', 'dekor'], ['рамы', 'frames', 'ramy'], ['двери', 'doors', 'drzwi'], ['цоколь', 'plinth', 'cokół'],
  ['Покраска (low-poly — цвет, реализм — тон текстуры)', 'Paint (low-poly = colour, realistic = texture tint)', 'Malowanie (low-poly = kolor, realizm = odcień tekstury)'],
  ['Покрасить', 'Paint', 'Pomaluj'], ['🎲 Случайно', '🎲 Random', '🎲 Losowo'], ['Сбросить', 'Reset', 'Resetuj'], ['План этажей', 'Floor plans', 'Plany pięter'], ['комнат', 'rooms', 'pokoi'],
  ['лестница', 'stairs', 'schody'], ['лифт', 'lift', 'winda'], ['фасад', 'facade', 'fasada'], ['покраска', 'paint', 'malowanie'], ['случайная покраска', 'random paint', 'losowe malowanie'],
  ['покраска сброшена', 'paint reset', 'malowanie zresetowane'], ['Новый:', 'New:', 'Nowy:'], ['Крепление:', 'Attach to:', 'Mocowanie:'], ['Куда', 'Where', 'Gdzie'], ['к элементу', 'to element', 'do elementu'],
  ['— свободно —', '— free —', '— swobodnie —'], ['якорь', 'anchor', 'kotwica'], ['Добавить', 'Add', 'Dodaj'], ['добавлен', 'added', 'dodano'],
  ['Готовые здания (макросы)', 'Ready buildings (macros)', 'Gotowe budynki (makra)'], ['Конструкции', 'Structures', 'Konstrukcje'], ['Окна и двери', 'Windows and doors', 'Okna i drzwi'],
  ['Крыши, купола, шпили', 'Roofs, domes, spires', 'Dachy, kopuły, iglice'], ['Колонны и портики', 'Columns and porticoes', 'Kolumny i portyki'], ['Декор и фасад', 'Decor and facade', 'Dekor i fasada'],
  ['Примитивы (любые формы)', 'Primitives (any shapes)', 'Prymitywy (dowolne kształty)'],
  ['Фильтр: эпоха / территория (вкладка «Библиотека»)', 'Filter: period / region (Library tab)', 'Filtr: epoka / region (zakładka „Biblioteka”)'],
  ['Применить стиль', 'Apply style', 'Zastosuj styl'], ['+ к миксу', '+ to mix', '+ do miksu'], ['микс стилей', 'style mix', 'miks stylów'], ['добавлен макрос', 'macro added', 'dodano makro'], ['стиль', 'style', 'styl'],
  ['Название нового проекта:', 'New project name:', 'Nazwa nowego projektu:'], ['переименован', 'renamed', 'zmieniono nazwę'],
  ['случайная покраска фасадов', 'random facade paint', 'losowe malowanie fasad'], ['новый сид случайностей', 'new random seed', 'nowe ziarno losowości'], ['интерьер для всех объёмов', 'interior for all volumes', 'wnętrza dla wszystkich brył'],
  ['Интерьер создан. Ползунок «Срез» показывает этажи изнутри; план — в свойствах элемента interior.', 'Interior created. The “Cut” slider shows the floors inside; the plan is in the interior element properties.', 'Wnętrze utworzone. Suwak „Przekrój” pokazuje piętra; plan jest we właściwościach elementu interior.'],
  ['состаривание', 'weathering', 'postarzanie'], ['интерьер включён', 'interior on', 'wnętrze włączone'], ['интерьер выключен', 'interior off', 'wnętrze wyłączone'],
  ['окна: затычка', 'windows: plug', 'okna: zaślepka'], ['окна: прозрачные', 'windows: clear', 'okna: przezroczyste'], ['декали', 'decals', 'naklejki'],
  ['материалов. Промпты:', 'materials. Prompts:', 'materiałów. Prompty:'], ['. Положите PNG в указанные папки.', '. Put the PNGs into the listed folders.', '. Umieść pliki PNG w podanych folderach.'],
  ['детализация', 'detail', 'szczegółowość'], ['Целевое число треугольников:', 'Target triangle count:', 'Docelowa liczba trójkątów:'], ['Есть проблемы:', 'There are problems:', 'Są problemy:'],
  ['Экспортировать всё равно?', 'Export anyway?', 'Eksportować mimo to?'],
  ['грязь', 'dirt', 'brud'], ['копоть', 'soot', 'sadza'], ['мох', 'moss', 'mech'], ['ржавчина', 'rust', 'rdza'], ['подтёки', 'streaks', 'zacieki'], ['трещины', 'cracks', 'pęknięcia'],
  ['облупленная краска', 'peeling paint', 'łuszcząca się farba'], ['граффити', 'graffiti', 'graffiti'], ['плакаты', 'posters', 'plakaty'], ['потёртости', 'scuffs', 'otarcia'],
  ['без текстуры', 'no texture', 'bez tekstury'], ['своя', 'own', 'własna'], ['своя (нет файла)', 'own (no file)', 'własna (brak pliku)'], ['Нет материалов (включите «Реализм»).', 'No materials (switch on “Realistic”).', 'Brak materiałów (włącz „Realizm”).'],
  ['текстуры включены', 'textures on', 'tekstury włączone'], ['текстуры выключены', 'textures off', 'tekstury wyłączone'], ['вкл.', 'on', 'wł.'], ['выкл.', 'off', 'wył.'], ['текстура', 'texture', 'tekstura'],
  ['верх (крыша / площадка)', 'top (roof / platform)', 'góra (dach / platforma)'], ['Грань', 'Face', 'Ściana'], ['На грани:', 'On this face:', 'Na ścianie:'], ['+ сюда', '+ here', '+ tutaj'],
  ['Добавить на эту грань в место клика', 'Add to this face at the clicked spot', 'Dodaj na tę ścianę w miejscu kliknięcia'], ['Снять выделение грани', 'Deselect the face', 'Odznacz ścianę'],
  ['Пометка на этой грани: ИИ поменяет только её', 'A mark on this face: the AI changes only it', 'Znacznik na tej ścianie: AI zmieni tylko ją'],
  ['💬 ИИ: изменить эту грань', '💬 AI: change this face', '💬 AI: zmień tę ścianę'], ['убрать окна', 'remove windows', 'usuń okna'], ['все окна', 'all windows', 'wszystkie okna'],
  ['случайно (часть заложена)', 'random (some bricked up)', 'losowo (część zamurowana)'], ['случайно, симметрично', 'random, symmetric', 'losowo, symetrycznie'], ['шахматка', 'checkerboard', 'szachownica'],
  ['через одно', 'every other', 'co drugie'], ['по формуле…', 'by formula…', 'według wzoru…'],
  ['Формула: c — столбец, r — ряд (с 0), cols, rows. Истина = окно. Например: (c + r) % 2 == 0', 'Formula: c = column, r = row (from 0), cols, rows. True = window. E.g. (c + r) % 2 == 0', 'Wzór: c = kolumna, r = rząd (od 0), cols, rows. Prawda = okno. Np. (c + r) % 2 == 0'],
  ['Формула для всех сеток окон. c — столбец, r — ряд (с 0), cols, rows, n. Истина = окно.', 'Formula for all window grids. c = column, r = row (from 0), cols, rows, n. True = window.', 'Wzór dla wszystkich siatek okien. c = kolumna, r = rząd (od 0), cols, rows, n. Prawda = okno.'],
  ['Примеры:', 'Examples:', 'Przykłady:'], ['окна на', 'windows on', 'okna na'], ['окна:', 'windows:', 'okna:'], ['формы зданий:', 'building shapes:', 'kształty budynków:'],
  ['без элемента (точка в пространстве)', 'no element (a point in space)', 'bez elementu (punkt w przestrzeni)'], ['что здесь сделать', 'what to do here', 'co tu zrobić'], ['Удалить пометку', 'Delete the mark', 'Usuń znacznik'],
  ['рисунок', 'drawing', 'rysunek'], ['точка', 'point', 'punkt'],
  ['Пометки: клик — точка, протянуть — нарисовать; камера — правая кнопка мыши', 'Marks: click = point, drag = draw; camera = right mouse button', 'Znaczniki: klik = punkt, przeciągnij = rysuj; kamera = prawy przycisk'],
  ['модель (по умолчанию)', 'model (default)', 'model (domyślny)'], ['модель (имя у провайдера)', 'model (provider name)', 'model (nazwa u dostawcy)'], ['ключ сохранён (ввести новый)', 'key saved (enter a new one)', 'klucz zapisany (wpisz nowy)'],
  ['API-ключ (не обязателен)', 'API key (optional)', 'Klucz API (opcjonalny)'], ['проверяю вход…', 'checking sign-in…', 'sprawdzam logowanie…'], ['не установлен', 'not installed', 'nie zainstalowano'],
  ['(не установлен)', '(not installed)', '(nie zainstalowano)'], ['✓ вход выполнен', '✓ signed in', '✓ zalogowano'], ['не выполнен вход', 'not signed in', 'nie zalogowano'],
  ['Идёт установка в отдельном окне. Когда закончится, нажмите «Войти».', 'Installing in a separate window. When it finishes, press “Sign in”.', 'Instalacja w osobnym oknie. Po zakończeniu naciśnij „Zaloguj”.'],
  ['Открылось окно входа: войдите в аккаунт в браузере, затем закройте окно и пишите в чат.', 'A sign-in window opened: sign in in the browser, then close the window and write in the chat.', 'Otworzyło się okno logowania: zaloguj się w przeglądarce, zamknij okno i pisz na czacie.'],
  ['Новый разговор.', 'New conversation.', 'Nowa rozmowa.'], ['чат:', 'chat:', 'czat:'],
  ['✓ Модель цельная: нет висящих частей и ошибок', '✓ The model is solid: no floating parts or errors', '✓ Model jest spójny: brak wiszących części i błędów'], ['✗ Проблем:', '✗ Problems:', '✗ Problemy:'],
  ['Треугольников:', 'Triangles:', 'Trójkątów:'], ['после оптимизации', 'after optimisation', 'po optymalizacji'], ['компонентов', 'components', 'komponentów'], ['размер', 'size', 'rozmiar'],
  ['замкнутая (watertight): да', 'watertight: yes', 'szczelny (watertight): tak'], ['изменение', 'change', 'zmiana'], ['скриншоты', 'screenshots', 'zrzuty'], ['проверка', 'check', 'kontrola'],
  ['экспорт', 'export', 'eksport'], ['текстуры', 'textures', 'tekstury'], ['ИИ пишет', 'AI writes', 'AI pisze'], ['камера', 'camera', 'kamera'], ['ошибка', 'error', 'błąd'], ['связь', 'connection', 'połączenie'],
  // periods / regions from the server
  ['Древность', 'Antiquity', 'Starożytność'], ['Средневековье', 'Middle Ages', 'Średniowiecze'], ['Новое время', 'Early modern', 'Nowożytność'], ['XIX век', '19th century', 'XIX wiek'],
  ['XX век', '20th century', 'XX wiek'], ['Современность', 'Contemporary', 'Współczesność'], ['Западная Европа', 'Western Europe', 'Europa Zachodnia'], ['Северная Европа', 'Northern Europe', 'Europa Północna'],
  ['Восточная Европа', 'Eastern Europe', 'Europa Wschodnia'], ['Россия / СССР', 'Russia / USSR', 'Rosja / ZSRR'], ['Средиземноморье', 'Mediterranean', 'Śródziemnomorze'], ['Кавказ', 'Caucasus', 'Kaukaz'],
  ['Ближний Восток', 'Middle East', 'Bliski Wschód'], ['Северная Африка', 'North Africa', 'Afryka Północna'], ['Центральная Азия', 'Central Asia', 'Azja Środkowa'], ['Южная Азия', 'South Asia', 'Azja Południowa'],
  ['Восточная Азия', 'East Asia', 'Azja Wschodnia'], ['Америка', 'Americas', 'Ameryka'], ['Весь мир', 'Worldwide', 'Cały świat'], ['Игры', 'Games', 'Gry'],
  ['до н.э.', 'BC', 'p.n.e.'], ['н.в.', 'now', 'obecnie'], ['макрос', 'macro', 'makro'], ['(макрос)', '(macro)', '(makro)'],
  ['— вход аккаунтом Claude', '— sign in with a Claude account', '— logowanie kontem Claude'],
  ['— вход аккаунтом OpenAI', '— sign in with an OpenAI account', '— logowanie kontem OpenAI'],
  ['— вход аккаунтом Google', '— sign in with a Google account', '— logowanie kontem Google'],
  ['(любые модели)', '(any models)', '(dowolne modele)'], ['(локально)', '(local)', '(lokalnie)'],
  ['Свой OpenAI-совместимый URL', 'Custom OpenAI-compatible URL', 'Własny URL zgodny z OpenAI'],
  // new: settings, export, autosave, game styles
  ['Настройки', 'Settings', 'Ustawienia'], ['Язык', 'Language', 'Język'], ['Тема', 'Theme', 'Motyw'], ['Тёмные', 'Dark', 'Ciemne'], ['Светлые', 'Light', 'Jasne'],
  ['Язык и тема сохраняются на этом компьютере.', 'Language and theme are saved on this computer.', 'Język i motyw są zapisywane na tym komputerze.'],
  ['Графит', 'Graphite', 'Grafit'], ['Полночь', 'Midnight', 'Północ'], ['Лес', 'Forest', 'Las'], ['Баклажан', 'Aubergine', 'Bakłażan'], ['Уголь и янтарь', 'Coal & amber', 'Węgiel i bursztyn'],
  ['Бумага', 'Paper', 'Papier'], ['Небо', 'Sky', 'Niebo'], ['Мята', 'Mint', 'Mięta'], ['Песок', 'Sand', 'Piasek'], ['Роза', 'Rose', 'Róża'],
  ['Только выбранное', 'Selection only', 'Tylko zaznaczone'], ['Экспортировать только выбранный элемент (и всё, что к нему прикреплено)', 'Export only the selected element (and everything attached to it)', 'Eksportuj tylko zaznaczony element (i wszystko, co jest do niego przymocowane)'],
  ['glTF (JSON + буферы)', 'glTF (JSON + buffers)', 'glTF (JSON + bufory)'], ['OBJ (почти везде, Roblox Studio)', 'OBJ (almost everywhere, Roblox Studio)', 'OBJ (prawie wszędzie, Roblox Studio)'],
  ['PLY (с цветами)', 'PLY (with colours)', 'PLY (z kolorami)'], ['OFF (простой меш)', 'OFF (plain mesh)', 'OFF (prosta siatka)'], ['3MF (3D-печать)', '3MF (3D printing)', '3MF (druk 3D)'],
  ['DAE / Collada (SketchUp, старые движки)', 'DAE / Collada (SketchUp, older engines)', 'DAE / Collada (SketchUp, starsze silniki)'], ['📂 Открыть папку экспорта', '📂 Open the export folder', '📂 Otwórz folder eksportu'],
  ['Сначала выберите элемент в сцене или в дереве.', 'Select an element in the scene or in the tree first.', 'Najpierw wybierz element w scenie lub w drzewie.'],
  ['Сохранено:', 'Saved:', 'Zapisano:'], ['🕘 Автосохранения…', '🕘 Autosaves…', '🕘 Autozapisy…'], ['Вернуть проект к этому автосохранению?', 'Restore the project to this autosave?', 'Przywrócić projekt do tego autozapisu?'],
  ['восстановлено автосохранение', 'autosave restored', 'przywrócono autozapis'], ['нет автосохранений', 'no autosaves', 'brak autozapisów'],
  ['Проект ▾', 'Project ▾', 'Projekt ▾'], ['Здание ▾', 'Building ▾', 'Budynek ▾'], ['Украшения ▾', 'Decorations ▾', 'Dekoracje ▾'],
  ['⬇ Экспорт ▾', '⬇ Export ▾', '⬇ Eksport ▾'], ['Показ ▾', 'Show ▾', 'Widok ▾'], ['Новый проект', 'New project', 'Nowy projekt'],
  ['📄 Скачать отчёт', '📄 Download report', '📄 Pobierz raport'], ['+ стиль', '+ style', '+ styl'],
  ['⬇ Убрать висящие части', '⬇ Fix floating parts', '⬇ Usuń wiszące części'], ['Опустить висящие в воздухе части на то, что под ними', 'Lower parts hanging in the air onto what is below', 'Opuść wiszące części na to, co pod nimi'],
  ['Показывать украшения', 'Show decorations', 'Pokaż dekoracje'], ['✨ Расставить автоматически', '✨ Place automatically', '✨ Rozmieść automatycznie'],
  ['Плотность', 'Density', 'Gęstość'], ['Убрать расставленные', 'Remove placed', 'Usuń rozmieszczone'],
  ['Отдельные украшения — в Библиотеке, раздел «Украшения».', 'Single decorations are in the Library, section “Decorations”.', 'Pojedyncze dekoracje są w Bibliotece, sekcja „Dekoracje”.'],
  ['Украшения и мелкие объекты', 'Decorations and small objects', 'Dekoracje i drobne obiekty'], ['Журнал', 'Log', 'Dziennik'], ['Снимки', 'Shots', 'Zrzuty'],
  ['Потрачено на проект:', 'Spent on the project:', 'Wydano na projekt:'], ['токенов', 'tokens', 'tokenów'], ['вход', 'in', 'wejście'], ['выход', 'out', 'wyjście'],
  ['запуск(ов) по подписке', 'subscription run(s)', 'uruchomień w abonamencie'], ['запусков ИИ:', 'AI runs:', 'uruchomień AI:'],
  ['ИИ ещё не работал над этим проектом.', 'The AI has not worked on this project yet.', 'AI jeszcze nie pracowało nad tym projektem.'],
  ['Отчёт:', 'Report:', 'Raport:'], ['по подписке Claude (≈ цена API)', 'Claude subscription (≈ API price)', 'abonament Claude (≈ cena API)'],
  ['по подписке ChatGPT', 'ChatGPT subscription', 'abonament ChatGPT'], ['цена у провайдера', 'price at the provider', 'cena u dostawcy'],
  ['токены:', 'tokens:', 'tokeny:'], ['инстр.', 'tools', 'narz.'],
  ['Сборка', 'Build', 'Budowa'], ['Сборщик', 'Builder', 'Budowniczy'], ['Цельный', 'Solid', 'Lity'], ['Из кирпичиков', 'From bricks', 'Z klocków'],
  ['Цельный — сварная оболочка; из кирпичиков — всё собрано из кубиков, как в воксельных и блочных играх', 'Solid = welded shell; from bricks = everything made of cubes, like voxel and block games', 'Lity = spawana powłoka; z klocków = wszystko z sześcianów, jak w grach wokselowych i klockowych'],
  ['Кирпич', 'Brick', 'Klocek'], ['Удалять невидимые грани', 'Remove hidden faces', 'Usuwaj niewidoczne ściany'],
  ['Выкл. — каждый кирпич остаётся полным кубом (грани на гранях): тяжелее, но каждый кирпич можно сделать отдельным объектом.', 'Off = every brick stays a full cube (faces on faces): heavier, but each brick can become its own object.', 'Wył. = każdy klocek zostaje pełnym sześcianem (ściany na ścianach): ciężej, ale każdy klocek może być osobnym obiektem.'],
  ['Двери', 'Doors', 'Drzwi'], ['Двери — отдельные объекты на петлях', 'Doors are separate objects on hinges', 'Drzwi to osobne obiekty na zawiasach'],
  ['🚪 Открыть / закрыть все двери', '🚪 Open / close all doors', '🚪 Otwórz / zamknij wszystkie drzwi'],
  ['Клик по двери в сцене открывает её. В экспорте каждая створка — свой узел с точкой петли и углом открытия (файл .objects.json) — для анимации в игре.', 'Click a door in the scene to open it. In exports every leaf is its own node with the hinge point and opening angle (.objects.json) — for animation in a game.', 'Kliknij drzwi w scenie, aby je otworzyć. W eksporcie każde skrzydło to osobny węzeł z punktem zawiasu i kątem otwarcia (.objects.json) — do animacji w grze.'],
  ['Разрушаемость', 'Destructibility', 'Zniszczalność'], ['Разрушаемое здание', 'Destructible building', 'Budynek zniszczalny'], ['Насколько', 'How much', 'Jak bardzo'],
  ['слабо — 12 кусков', 'light — 12 pieces', 'słabo — 12 kawałków'], ['средне — 40 кусков', 'medium — 40 pieces', 'średnio — 40 kawałków'],
  ['сильно — 100 кусков', 'heavy — 100 pieces', 'mocno — 100 kawałków'], ['в щепки — 250 кусков', 'to splinters — 250 pieces', 'w drzazgi — 250 kawałków'],
  ['каждый кирпич отдельно', 'every brick separately', 'każdy klocek osobno'], ['Как', 'How', 'Jak'], ['трещинами (куски)', 'cracks (chunks)', 'pęknięcia (kawałki)'],
  ['по элементам (стены, крыша, окна)', 'by elements (walls, roof, windows)', 'według elementów (ściany, dach, okna)'],
  ['Показать куски', 'Show pieces', 'Pokaż kawałki'], ['💥 Взорвать', '💥 Blow up', '💥 Wysadź'], ['↺ Собрать', '↺ Reassemble', '↺ Złóż'], ['Разлёт', 'Spread', 'Rozrzut'],
  ['Больше кусков — реалистичнее, но тяжелее для игры. В экспорте каждый кусок — отдельный объект с центром масс и объёмом (для физики), места разлома — материал «rubble».', 'More pieces look more real but are heavier for a game. In exports every piece is its own object with centre of mass and volume (for physics); break surfaces use the “rubble” material.', 'Więcej kawałków wygląda realniej, ale obciąża grę. W eksporcie każdy kawałek to osobny obiekt ze środkiem masy i objętością (dla fizyki); miejsca pęknięć mają materiał „rubble”.'],
  ['Сначала включите «Разрушаемое здание».', 'Switch on “Destructible building” first.', 'Najpierw włącz „Budynek zniszczalny”.'], ['кусков', 'pieces', 'kawałków'],
  ['Каждое изменение сразу сохраняется; здесь — снимки проекта, к которым можно вернуться.', 'Every change is saved at once; these are project snapshots you can go back to.', 'Każda zmiana jest od razu zapisywana; tu są migawki projektu, do których można wrócić.'],
];

const exact = new Map();
const phrases = [];
const norm = (s) => s.replace(/\s+/g, ' ').trim();
const col = { en: 1, pl: 2 }[lang];
if (col) {
  for (const row of D) {
    exact.set(norm(row[0]), row[col]);
    if (row[0].length >= 4) phrases.push([row[0], row[col]]);
  }
  phrases.sort((a, b) => b[0].length - a[0].length);
}
const CYR = /[А-Яа-яЁё]/;

/** Translate one string (exact match, else known phrases inside it). Russian UI: returned as is. */
export function tr(s) {
  if (!col || !s || !CYR.test(s)) return s;
  const n = norm(s);
  if (exact.has(n)) return s.replace(n, exact.get(n)).replace(/^\s+|\s+$/g, (w) => w);
  let out = s;
  for (const [ru, t] of phrases) if (out.includes(ru)) out = out.split(ru).join(t);
  return out;
}

const SKIP = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'PRE']);
function skipNode(el) {  // user / AI text is not translated: chat, project names, the license text
  return !el || SKIP.has(el.tagName) || el.closest?.('#chatLog, #aboutLic, .no-tr');
}
function translateTree(root) {
  if (root.nodeType === 3) {
    if (!skipNode(root.parentElement)) { const t = tr(root.nodeValue); if (t !== root.nodeValue) root.nodeValue = t; }
    return;
  }
  if (root.nodeType !== 1 || skipNode(root)) return;
  for (const a of ['title', 'placeholder', 'aria-label']) {
    const v = root.getAttribute?.(a);
    if (v) { const t = tr(v); if (t !== v) root.setAttribute(a, t); }
  }
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    if (n.nodeType === 1) {
      for (const a of ['title', 'placeholder', 'aria-label']) {
        const v = n.getAttribute(a);
        if (v && !skipNode(n)) { const t = tr(v); if (t !== v) n.setAttribute(a, t); }
      }
    } else if (!skipNode(n.parentElement)) {
      const t = tr(n.nodeValue);
      if (t !== n.nodeValue) n.nodeValue = t;
    }
  }
}

export function initI18n() {
  document.documentElement.lang = lang;
  if (!col) return;
  translateTree(document.body);
  document.title = tr(document.title);
  new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type === 'childList') m.addedNodes.forEach(translateTree);
      else if (m.type === 'characterData') translateTree(m.target);
      else if (m.type === 'attributes') translateTree(m.target);
    }
  }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['title', 'placeholder'] });
  for (const fn of ['prompt', 'confirm', 'alert']) {
    const orig = window[fn].bind(window);
    window[fn] = (msg, ...rest) => orig(tr(String(msg ?? '')), ...rest);
  }
}

export function setLang(l) {
  try { localStorage.setItem('pazl.lang', l); } catch { /* not saved */ }
  location.reload();
}
