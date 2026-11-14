(() => {
  'use strict';
  if (window.__chatgptThemesManager) return;
  window.__chatgptThemesManager = true;
  const presets = __THEME_PRESETS__;
  const KEY = 'chatgpt-themes.settings.v1';
  const STYLE_ID = 'sumerki-bundled-theme';
  const surfaces = 'body, .bg-surface.h-full, main[class*="MainContentSurface-"]';
  const defaults = {theme: 'sumerki', motion: true, geometry: true, duration: 48};
  let storageAvailable = true;
  let root, host, panel, lastFocused;

  function normalize(value) {
    const v = value && typeof value === 'object' ? value : {};
    return {
      theme: v.theme === 'native' || presets.some(t => t.id === v.theme) ? v.theme : defaults.theme,
      motion: typeof v.motion === 'boolean' ? v.motion : defaults.motion,
      geometry: typeof v.geometry === 'boolean' ? v.geometry : defaults.geometry,
      duration: Number.isFinite(v.duration) ? Math.max(20, Math.min(120, v.duration)) : defaults.duration,
    };
  }
  function load() {
    try { return normalize(JSON.parse(localStorage.getItem(KEY))); }
    catch (_) { return normalize(null); }
  }
  let state = load();
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); storageAvailable = true; }
    catch (_) { storageAvailable = false; }
  }
  function apply() {
    let style = document.getElementById(STYLE_ID);
    if (state.theme === 'native') {
      style?.remove();
      return;
    }
    if (!style) {
      style = document.createElement('style');
      style.id = STYLE_ID;
      document.head.appendChild(style);
    }
    const theme = presets.find(t => t.id === state.theme);
    let css = theme.css + `\n${surfaces}{animation-duration:${state.duration}s !important;}`;
    if (!state.motion) css += `\n${surfaces}{animation:none !important;}`;
    if (!state.geometry) css += `\n${surfaces}{background-image:none !important;animation:none !important;}`;
    if (style.textContent !== css) style.textContent = css;
  }
  function synchronizeControls() {
    if (!root) return;
    root.querySelectorAll('[data-theme]').forEach(button => {
      const selected = button.dataset.theme === state.theme;
      button.setAttribute('aria-pressed', String(selected));
    });
    root.getElementById('motion').checked = state.motion;
    root.getElementById('geometry').checked = state.geometry;
    root.getElementById('duration').value = String(state.duration);
    root.getElementById('duration-value').textContent = `${state.duration} с`;
    const native = state.theme === 'native';
    root.getElementById('motion').disabled = native || !state.geometry;
    root.getElementById('geometry').disabled = native;
    root.getElementById('duration').disabled = native || !state.geometry || !state.motion;
    root.getElementById('status').textContent = storageAvailable
      ? 'Выбор сохраняется автоматически'
      : 'Не удалось сохранить выбор. Он действует до закрытия окна.';
  }
  function update(patch) {
    state = normalize({...state, ...patch});
    apply(); save(); synchronizeControls();
  }
  function close() {
    panel.hidden = true;
    host.style.display = 'none';
    if (lastFocused?.isConnected) lastFocused.focus();
  }
  function open() {
    if (!root || !panel.hidden) return;
    lastFocused = document.activeElement;
    panel.hidden = false;
    host.style.display = 'flex';
    synchronizeControls();
    root.getElementById('close').focus();
  }
  function mount() {
    if (!document.body || document.getElementById('chatgpt-themes-manager')) return;
    host = document.createElement('div');
    host.id = 'chatgpt-themes-manager';
    host.style.cssText = 'position:fixed;inset:0;z-index:2147483000;display:none;align-items:center;justify-content:center;background:#0006;-webkit-app-region:no-drag;';
    root = host.attachShadow({mode: 'open'});
    root.innerHTML = `<style>
      :host{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#eeeaf6;font-size:13px;color-scheme:dark;}
      *{box-sizing:border-box} [hidden]{display:none!important}
      button,input,label{font:inherit} button,input{accent-color:#b9a1ff}
      button{cursor:pointer;color:inherit} button:focus-visible,input:focus-visible{outline:2px solid #c7b6ff;outline-offset:3px}
      #panel{pointer-events:auto;width:min(380px,calc(100vw - 32px));max-height:calc(100vh - 48px);overflow:auto;padding:18px;border:1px solid #ffffff24;border-radius:18px;background:#211d2bf5;box-shadow:0 16px 56px #0006;}
      header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}h2{font-size:17px;margin:0;font-weight:650;letter-spacing:-.3px}
      #close{border:0;background:none;padding:3px 6px;font-size:20px;line-height:1;color:#b9afca}
      #themes{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:17px}
      .theme{display:flex;flex-direction:column;align-items:flex-start;gap:10px;padding:12px;border-radius:12px;border:1px solid #ffffff18;background:#ffffff05;}
      .theme[aria-pressed=true]{border-color:#baa4ff;background:#b9a1ff16;box-shadow:0 0 0 1px #baa4ff inset}
      .swatch{display:block;width:100%;height:28px;border-radius:6px;background:var(--swatch);border:1px solid #ffffff14}
      .row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:13px 0}.row input{width:17px;height:17px;margin:0}
      .speed{display:block;border-top:1px solid #ffffff14;padding-top:14px}.speed div{display:flex;justify-content:space-between;color:#c5bdcf}.speed input{width:100%;margin:12px 0 2px}
      input:disabled{opacity:.35;cursor:default}#status{margin:14px 0 0;font-size:11px;line-height:1.5;color:#a49aaf}
      @media(max-height:400px){:host #panel{max-height:calc(100vh - 115px)}}
    </style>
    <section id="panel" role="dialog" aria-modal="true" aria-label="Темы оформления" hidden>
      <header><h2>Оформление</h2><button id="close" type="button" aria-label="Закрыть">×</button></header>
      <div id="themes" role="group" aria-label="Выбор темы"></div>
      <label class="row" for="geometry">Геометрический фон<input id="geometry" type="checkbox"></label>
      <label class="row" for="motion">Анимация<input id="motion" type="checkbox"></label>
      <label class="speed" for="duration"><div><span>Длительность цикла</span><output id="duration-value"></output></div><input id="duration" type="range" min="20" max="120" step="4"></label>
      <p id="status" role="status"></p>
    </section>`;
    panel = root.getElementById('panel');
    const themes = [{id:'native',name:'Стандартная',swatch:'#787878'}, ...presets];
    themes.forEach(theme => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'theme'; button.dataset.theme = theme.id;
      const swatch = document.createElement('span');
      swatch.className = 'swatch'; swatch.style.setProperty('--swatch', theme.swatch);
      const label = document.createElement('span'); label.textContent = theme.name;
      button.append(swatch, label);
      button.addEventListener('click', () => update({theme:theme.id}));
      root.getElementById('themes').appendChild(button);
    });
    root.getElementById('close').addEventListener('click', close);
    root.getElementById('motion').addEventListener('change', e => update({motion:e.target.checked}));
    root.getElementById('geometry').addEventListener('change', e => update({geometry:e.target.checked}));
    root.getElementById('duration').addEventListener('input', e => update({duration:Number(e.target.value)}));
    root.addEventListener('keydown', e => {
      if(e.key === 'Escape') {e.preventDefault();e.stopPropagation();close();}
      if(e.key === 'Tab') {
        const items = [...panel.querySelectorAll('button,input')].filter(e => !e.disabled);
        const index = items.indexOf(root.activeElement);
        if ((e.shiftKey && index <= 0) || (!e.shiftKey && index === items.length - 1)) {
          e.preventDefault(); (e.shiftKey ? items.at(-1) : items[0]).focus();
        }
      }
    });
    host.addEventListener('pointerdown', e => { if(e.composedPath()[0] === host) close(); });
    window.addEventListener('chatgpt-themes:open', open);
    document.body.appendChild(host);
    synchronizeControls();
  }
  window.addEventListener('storage', e => {
    if (e.key === KEY || e.key === null) { state = load(); apply(); synchronizeControls(); }
  });
  apply();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true});
  else mount();
})();
