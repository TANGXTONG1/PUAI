(() => {
  'use strict';

  // The personal homepage and PUAI are on the same origin and share this choice.
  const storageKey = 'yuanrong.analytics-consent.v1';
  let tabChoice = null;
  let prompted = false;
  let panel;
  let opener;

  function privacySignal() {
    return navigator.globalPrivacyControl === true ||
      [navigator.doNotTrack, window.doNotTrack, navigator.msDoNotTrack].some(
        value => value === '1' || value === 'yes'
      );
  }

  function choice() {
    if (privacySignal()) return 'denied';
    if (tabChoice !== null) return tabChoice;
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved === 'granted' || saved === 'denied') return saved;
    } catch {
      // Without storage or an explicit choice, measurement remains off.
    }
    return 'unset';
  }

  function clearAnalyticsCookies() {
    for (const name of ['_ga', '_ga_G826FL7DY2']) {
      for (const domain of ['', '; Domain=' + location.hostname]) {
        try {
          document.cookie = name + '=; Max-Age=0; Path=/' + domain + '; SameSite=Lax';
        } catch {
          // Storage can be blocked entirely.
        }
      }
    }
  }

  function notify() {
    const current = choice();
    window.dispatchEvent(new CustomEvent('puai-metrics-consent-change', {
      detail: { choice: current, allowed: current === 'granted' }
    }));
  }

  function save(next) {
    if (next === 'granted' && privacySignal()) return;
    try {
      localStorage.setItem(storageKey, next);
      tabChoice = null;
    } catch {
      tabChoice = next;
    }
    close();
    notify();
    if (next === 'denied') clearAnalyticsCookies();
  }

  function close() {
    if (!panel || panel.hidden) return;
    const restoreFocus = panel.contains(document.activeElement);
    panel.hidden = true;
    if (restoreFocus && opener?.isConnected) opener.focus({ preventScroll: true });
    opener = null;
  }

  function dismiss() {
    if (panel && !panel.hidden) {
      close();
      window.dispatchEvent(new Event('puai-metrics-dismiss'));
    }
  }

  function show(trigger, manual = false) {
    prompted = true;
    opener = trigger || document.activeElement;
    if (!panel) {
      panel = document.createElement('section');
      panel.dataset.puaiConsentPanel = '';
      panel.setAttribute('aria-labelledby', 'puai-consent-title');
      panel.innerHTML = '<button type="button" data-close aria-label="关闭统计设置">×</button>' +
        '<h2 id="puai-consent-title" tabindex="-1"></h2><p></p><div>' +
        '<button type="button" data-allow>允许统计</button>' +
        '<button type="button" data-deny>拒绝统计</button></div>';
      panel.querySelector('[data-close]').addEventListener('click', dismiss);
      panel.querySelector('[data-allow]').addEventListener('click', () => save('granted'));
      panel.querySelector('[data-deny]').addEventListener('click', () => save('denied'));
    }
    // In a modal viewer the rest of the document is inert, including a body-level prompt.
    const host = opener?.closest('dialog[open]') || document.body;
    if (panel.parentElement !== host) host.append(panel);
    const current = choice();
    const signal = privacySignal();
    const heading = panel.querySelector('h2');
    const deny = panel.querySelector('[data-deny]');
    heading.textContent = {
      unset: '允许统计按钮点击吗？', granted: '按钮点击统计已开启', denied: '按钮点击统计已关闭'
    }[current];
    panel.querySelector('p').textContent = signal
      ? '浏览器已发出停止跟踪信号。'
      : '使用 Google Analytics 的统计 Cookie，计算有多少人点过、点了几次。';
    panel.querySelector('[data-allow]').hidden = signal || current === 'granted';
    deny.hidden = current === 'denied';
    deny.textContent = current === 'granted' ? '撤回同意' : '拒绝统计';
    panel.hidden = false;
    if (manual) heading.focus({ preventScroll: true });
  }

  window.puaiMetricsConsent = choice;
  window.puaiMetricsAllowed = () => choice() === 'granted';
  window.puaiAskMetricsConsent = trigger => {
    if (choice() !== 'unset' || (prompted && panel.hidden)) return false;
    show(trigger);
    return true;
  };
  document.addEventListener('close', event => {
    if (panel?.parentElement === event.target && !event.target.open) dismiss();
  }, true);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !event.defaultPrevented) dismiss();
  });
  document.addEventListener('click', event => {
    const trigger = event.target.closest?.('[data-puai-privacy]');
    if (trigger) show(trigger, true);
  });
  window.addEventListener('storage', event => {
    if (event.key !== storageKey && event.key !== null) return;
    tabChoice = null;
    close();
    notify();
    if (choice() === 'denied') clearAnalyticsCookies();
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted) {
      close();
      notify();
    }
  });
})();
