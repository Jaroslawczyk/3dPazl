// 2D workshop "sprites": tools of this workspace. Filled in by its own task; see web/workspaces.js for ctx.
export function mount(el, ctx) {
  el.innerHTML = '<h4>Инструменты</h4><div class="hint">' + ctx.info.about + ' Инструменты появятся здесь.</div>';
}
