// Only the hosted pages have click metrics. The skill and exported reports work offline.
(() => {
  const surface = document.body.dataset.puaiSurface;
  if (location.origin !== 'https://xn--sxrw8m230b.com' || window !== window.top || !surface) return;

  const frameURL = new URL('metrics-frame.html', document.currentScript.src);
  let frame;
  let ready = false;
  let pending = [];

  function deliver() {
    if (!window.puaiMetricsAllowed?.() || !pending.length) return;
    if (!frame) {
      frame = document.createElement('iframe');
      frame.hidden = true;
      frame.title = 'PUAI 点击统计';
      frame.referrerPolicy = 'no-referrer';
      frame.src = frameURL.href;
      document.body.append(frame);
    }
    if (ready) {
      for (const action of pending) {
        frame.contentWindow.postMessage({ type: 'puai-click', action, surface }, location.origin);
      }
      pending = [];
    }
  }

  function clicked(action, button) {
    const consent = window.puaiMetricsConsent?.();
    if (consent === 'unset') {
      if (window.puaiAskMetricsConsent?.(button)) pending = [action];
      return;
    }
    if (consent !== 'granted') return;
    if (pending.length < 32) pending.push(action);
    deliver();
  }

  document.addEventListener('click', event => {
    if (!event.isTrusted || event.button !== 0) return;
    const button = event.target.closest?.('[data-puai-action]');
    if (!button || button.disabled || (button.type === 'submit' && button.form?.matches(':invalid'))) return;
    clicked(button.dataset.puaiAction, button);
  }, true);
  window.addEventListener('message', event => {
    if (!frame || event.source !== frame.contentWindow || event.origin !== location.origin ||
        event.data?.type !== 'puai-ready') return;
    ready = true;
    deliver();
  });
  window.addEventListener('puai-metrics-dismiss', () => { pending = []; });
  window.addEventListener('puai-metrics-consent-change', () => {
    if (window.puaiMetricsAllowed?.()) deliver();
    else {
      pending = [];
      ready = false;
      frame?.remove();
      frame = null;
    }
  });
})();
