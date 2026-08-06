(function () {
  'use strict';

  var SEO_TITLE_MIN = 50, SEO_TITLE_MAX = 60;
  var SEO_DESC_MIN  = 140, SEO_DESC_MAX  = 155;

  var STYLE = [
    '.seo-hint{margin-top:5px;font-size:13px;line-height:1.6;font-family:var(--font-family-primary,sans-serif)}',
    '.seo-counter{display:inline-flex;align-items:center;gap:8px}',
    '.seo-count{font-weight:700}',
    '.seo-kw-status{margin-top:4px}',
    '.seo-ok{color:#2ea84a}',
    '.seo-warn{color:#c07800}',
    '.seo-err{color:#c0000a}',
  ].join('');

  function injectStyles() {
    if (document.getElementById('seo-admin-styles')) return;
    var s = document.createElement('style');
    s.id = 'seo-admin-styles';
    s.textContent = STYLE;
    document.head.appendChild(s);
  }

  function getHint(fieldEl, hintId) {
    var el = document.getElementById(hintId);
    if (el) return el;
    var div = document.createElement('div');
    div.id = hintId;
    div.className = 'seo-hint';
    fieldEl.parentNode.insertBefore(div, fieldEl.nextSibling);
    return div;
  }

  // ── SEO Title counter ────────────────────────────────────────────────────
  function renderTitleCounter(input, hint) {
    var len = input.value.length;
    var cls, icon;
    if (len >= SEO_TITLE_MIN && len <= SEO_TITLE_MAX) {
      cls = 'seo-ok';  icon = '✅ Good';
    } else if (len > SEO_TITLE_MAX) {
      cls = 'seo-err'; icon = '⛔ Too long';
    } else {
      cls = 'seo-warn'; icon = '⚠️ Too short';
    }
    hint.innerHTML =
      '<span class="seo-counter">' +
        '<span class="seo-count ' + cls + '">' + len + '/' + SEO_TITLE_MAX + '</span>' +
        '<span class="' + cls + '">' + icon + '</span>' +
      '</span>';
  }

  // ── Meta Description counter ─────────────────────────────────────────────
  function renderDescCounter(input, hint) {
    var len = input.value.length;
    var cls, icon;
    if (len >= SEO_DESC_MIN && len <= SEO_DESC_MAX) {
      cls = 'seo-ok';  icon = '✅ Good';
    } else if (len > SEO_DESC_MAX) {
      cls = 'seo-err'; icon = '⛔ Too long';
    } else {
      cls = 'seo-warn'; icon = '⚠️ Too short';
    }
    hint.innerHTML =
      '<span class="seo-counter">' +
        '<span class="seo-count ' + cls + '">' + len + '/' + SEO_DESC_MAX + '</span>' +
        '<span class="' + cls + '">' + icon + '</span>' +
      '</span>';
  }

  // ── Focus Keyword in Title ───────────────────────────────────────────────
  function renderKwTitle(kwInput, titleInput, hint) {
    var kw = kwInput.value.trim().toLowerCase();
    if (!kw) {
      hint.innerHTML = '<span class="seo-kw-status seo-warn">⚠️ Enter a keyword to check presence in the SEO title.</span>';
      return;
    }
    var found = titleInput.value.toLowerCase().indexOf(kw) !== -1;
    hint.innerHTML = found
      ? '<span class="seo-kw-status seo-ok">✅ Keyword found in SEO title.</span>'
      : '<span class="seo-kw-status seo-err">❌ Keyword not found in SEO title.</span>';
  }

  // ── Focus Keyword in Description ─────────────────────────────────────────
  function renderKwDesc(kwInput, descInput, hint) {
    var kw = kwInput.value.trim().toLowerCase();
    if (!kw) {
      hint.innerHTML = '<span class="seo-kw-status seo-warn">⚠️ Enter a keyword to check presence in the meta description.</span>';
      return;
    }
    var found = descInput.value.toLowerCase().indexOf(kw) !== -1;
    hint.innerHTML = found
      ? '<span class="seo-kw-status seo-ok">✅ Keyword found in meta description.</span>'
      : '<span class="seo-kw-status seo-err">❌ Keyword not found in meta description.</span>';
  }

  // ── init ─────────────────────────────────────────────────────────────────
  function init() {
    injectStyles();

    var titleInput  = document.getElementById('id_seo_title');
    var descInput   = document.getElementById('id_seo_description');
    var kwTitleInput = document.getElementById('id_focus_keyword_title');
    var kwDescInput  = document.getElementById('id_focus_keyword_description');

    if (!titleInput || !descInput) return;

    // SEO Title counter
    var titleHint = getHint(titleInput, 'seo-title-hint');
    renderTitleCounter(titleInput, titleHint);
    titleInput.addEventListener('input', function () {
      renderTitleCounter(titleInput, titleHint);
      if (kwTitleInput) renderKwTitle(kwTitleInput, titleInput,
        document.getElementById('seo-kw-title-hint') || getHint(kwTitleInput, 'seo-kw-title-hint'));
    });

    // Meta Description counter
    var descHint = getHint(descInput, 'seo-desc-hint');
    renderDescCounter(descInput, descHint);
    descInput.addEventListener('input', function () {
      renderDescCounter(descInput, descHint);
      if (kwDescInput) renderKwDesc(kwDescInput, descInput,
        document.getElementById('seo-kw-desc-hint') || getHint(kwDescInput, 'seo-kw-desc-hint'));
    });

    // Focus Keyword in Title
    if (kwTitleInput) {
      var kwTitleHint = getHint(kwTitleInput, 'seo-kw-title-hint');
      renderKwTitle(kwTitleInput, titleInput, kwTitleHint);
      kwTitleInput.addEventListener('input', function () {
        renderKwTitle(kwTitleInput, titleInput, kwTitleHint);
      });
    }

    // Focus Keyword in Description
    if (kwDescInput) {
      var kwDescHint = getHint(kwDescInput, 'seo-kw-desc-hint');
      renderKwDesc(kwDescInput, descInput, kwDescHint);
      kwDescInput.addEventListener('input', function () {
        renderKwDesc(kwDescInput, descInput, kwDescHint);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Re-init when a collapsed fieldset is expanded
  document.addEventListener('click', function (e) {
    var h2 = e.target.closest && e.target.closest('h2');
    if (h2 && h2.closest('.module.collapse')) {
      setTimeout(init, 50);
    }
  });
})();
