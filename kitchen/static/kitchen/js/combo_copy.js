/* One tap to copy a combo card's emoji set. Works for any page that wraps its cards in [data-copy-grid].
   Uses the Clipboard API and falls back to a hidden textarea for older browsers. Nothing is sent anywhere. */
(function () {
  'use strict';

  function flash(btn) {
    var original = btn.dataset.label || btn.textContent;
    btn.dataset.label = original;
    btn.textContent = '✅ Copied!';
    setTimeout(function () { btn.textContent = original; }, 1800);
    if (window.showToast) window.showToast('Copied! Paste it anywhere.', '📋');
  }

  function fallback(text, btn) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
    document.body.removeChild(ta);
    if (ok) flash(btn);
    else btn.textContent = 'Press and hold to copy';
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-copy-grid] .combo-card__copy');
    if (!btn) return;
    var combo = btn.dataset.combo;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(combo).then(function () { flash(btn); }).catch(function () { fallback(combo, btn); });
    } else {
      fallback(combo, btn);
    }
  });
})();
