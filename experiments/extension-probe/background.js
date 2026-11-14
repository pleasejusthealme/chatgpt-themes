const allowed = new Set(['app://-/index.html', 'app://-/detached-window.html']);
const attached = new Set();
let busy = false;
function call(method, ...args) {
  return new Promise((resolve, reject) => {
    chrome.debugger[method](...args, result => {
      if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
      else resolve(result);
    });
  });
}
async function update() {
  if (busy) return;
  busy = true;
  try {
    const css = await (await fetch(chrome.runtime.getURL('theme.css'))).text();
    const targets = await call('getTargets');
    for (const target of targets) {
      if (target.type !== 'page' || !allowed.has(target.url)) continue;
      const debuggee = {targetId: target.id};
      try {
        if (!attached.has(target.id)) {
          await call('attach', debuggee, '1.3');
          attached.add(target.id);
        }
        const expression = `(() => {
          if (!document.head) return false;
          const id='sumerki-experimental-theme', css=${JSON.stringify(css)};
          let s=document.getElementById(id);
          if (s && s.textContent===css) return true;
          if (!s) {s=document.createElement('style');s.id=id;document.head.appendChild(s);}
          s.textContent=css;return true;
        })()`;
        await call('sendCommand', debuggee, 'Runtime.evaluate', {expression, returnByValue:true});
      } catch (error) {
        attached.delete(target.id);
        console.warn('Sumerki:', error.message);
      }
    }
  } catch (error) {
    console.warn('Sumerki:', error.message);
  } finally { busy = false; }
}
chrome.debugger.onDetach.addListener(source => attached.delete(source.targetId));
chrome.runtime.onInstalled.addListener(() => { chrome.alarms.create('sumerki', {periodInMinutes:0.5}); update(); });
chrome.runtime.onStartup.addListener(() => { chrome.alarms.create('sumerki', {periodInMinutes:0.5}); update(); });
chrome.alarms.onAlarm.addListener(alarm => { if (alarm.name==='sumerki') update(); });
setInterval(update, 2000);
update();
