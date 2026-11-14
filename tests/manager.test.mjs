import assert from 'node:assert/strict';

export function testManager({parseHTML, vm, script}) {
  let checks = 0;
  const values = new Map();
  function boot(storage = {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v)}) {
    const {window, document} = parseHTML('<html><head></head><body><div id="root">Chat</div></body></html>');
    delete window.__chatgptThemesManager;
    window.HTMLElement.prototype.focus = function () {};
    const context = vm.createContext({window,document,localStorage:storage,console});
    vm.runInContext(script,context);
    document.dispatchEvent(new window.Event('DOMContentLoaded'));
    const root = document.getElementById('chatgpt-themes-manager').shadowRoot;
    return {window,document,context,root,click:id=>root.querySelector(`[data-theme="${id}"]`).click()};
  }
  const a=boot();
  assert.ok(a.document.getElementById('sumerki-bundled-theme')); checks++;
  assert.equal(a.root.getElementById('panel').hidden,true);
  assert.equal(a.root.getElementById('open'),null);
  a.window.dispatchEvent(new a.window.Event('chatgpt-themes:open')); 
  assert.equal(a.root.getElementById('panel').hidden,false);checks++;
  a.click('native');assert.equal(a.document.getElementById('sumerki-bundled-theme'),null);checks++;
  a.click('ocean');assert.match(a.document.getElementById('sumerki-bundled-theme').textContent,/#101d27/);checks++;
  const motion=a.root.getElementById('motion');motion.checked=false;motion.dispatchEvent(new a.window.Event('change'));
  assert.match(a.document.getElementById('sumerki-bundled-theme').textContent,/animation:none !important/);checks++;
  const b=boot();assert.equal(b.root.querySelector('[data-theme="ocean"]').getAttribute('aria-pressed'),'true');
  assert.equal(b.root.getElementById('motion').checked,false);checks++;
  const geometry=b.root.getElementById('geometry');geometry.checked=false;geometry.dispatchEvent(new b.window.Event('change'));
  assert.match(b.document.getElementById('sumerki-bundled-theme').textContent,/background-image:none !important/);checks++;
  vm.runInContext(script,b.context);assert.equal(b.document.querySelectorAll('#chatgpt-themes-manager').length,1);checks++;
  b.window.dispatchEvent(new b.window.Event('chatgpt-themes:open'));b.root.getElementById('close').click();assert.equal(b.root.getElementById('panel').hidden,true);checks++;
  values.set('chatgpt-themes.settings.v1',JSON.stringify({theme:'unknown',duration:999}));
  const c=boot();assert.equal(c.root.getElementById('duration').value,'120');
  assert.equal(c.root.querySelector('[data-theme="sumerki"]').getAttribute('aria-pressed'),'true');checks++;
  const d=boot({getItem(){throw Error('blocked')},setItem(){throw Error('full')}});
  d.click('graphite');assert.match(d.root.getElementById('status').textContent,/Не удалось сохранить/);checks++;
  assert.equal(d.document.getElementById('root').textContent,'Chat');checks++;
  return {checks,passed:true};
}
