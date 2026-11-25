/* Emoji Art Editor: draw on a grid with emojis, then copy the result as text.
   Everything runs in the browser. Nothing is uploaded. */
(function () {
  'use strict';

  var root = document.getElementById('ea-app');
  if (!root) return;

  var MIN_SIZE = 4, MAX_SIZE = 40;
  var HISTORY_LIMIT = 100;

  var PALETTE = {
    '😀 Faces': ['😀', '😂', '🥰', '😍', '😎', '🤩', '😭', '😡', '🥺', '😴', '🤔', '😱', '🤯', '😇', '🥳', '😈'],
    '❤️ Hearts': ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '🩷', '🩵', '💖', '💔', '🔥', '⭐', '✨'],
    '🌿 Nature': ['🌸', '🌷', '🌹', '🌻', '🌿', '🍀', '🌲', '🌵', '🌊', '☁️', '🌙', '☀️', '🌈', '❄️', '🍂', '🪨'],
    '🍕 Food': ['🍎', '🍊', '🍋', '🍉', '🍓', '🍒', '🍑', '🥕', '🍕', '🍔', '🍩', '🍪', '🧁', '🍫', '🍦', '☕'],
    '🐱 Animals': ['🐱', '🐶', '🐰', '🐻', '🐼', '🦊', '🐸', '🐵', '🐥', '🦋', '🐝', '🐢', '🐙', '🐬', '🦄', '🐞'],
    '🟦 Blocks': ['⬛', '⬜', '🟥', '🟧', '🟨', '🟩', '🟦', '🟪', '🟫', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '⚫']
  };

  var el = {
    grid: document.getElementById('ea-grid'),
    palette: document.getElementById('ea-palette'),
    tabs: document.getElementById('ea-tabs'),
    brush: document.getElementById('ea-brush'),
    custom: document.getElementById('ea-custom'),
    cols: document.getElementById('ea-cols'),
    rows: document.getElementById('ea-rows'),
    emptyChar: document.getElementById('ea-empty'),
    status: document.getElementById('ea-status'),
    importBox: document.getElementById('ea-import-box'),
    importText: document.getElementById('ea-import-text'),
    file: document.getElementById('ea-import-file')
  };

  var state = {
    cols: 16,
    rows: 12,
    cells: [],
    brush: '❤️',
    tool: 'draw',
    zoom: 28,
    undo: [],
    redo: []
  };

  // ── helpers ──────────────────────────────────────────────────────────────
  function graphemes(text) {
    if (typeof Intl !== 'undefined' && Intl.Segmenter) {
      var seg = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
      return Array.from(seg.segment(text), function (s) { return s.segment; });
    }
    return Array.from(text);
  }

  function isBlank(g) { return !g || !g.trim(); }

  function emptyCells(n) { return new Array(n).fill(''); }

  function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }

  function say(message) {
    el.status.textContent = message;
    clearTimeout(say.t);
    say.t = setTimeout(function () { el.status.textContent = ''; }, 2600);
  }

  function snapshot() {
    return { cols: state.cols, rows: state.rows, cells: state.cells.slice() };
  }

  function restore(snap) {
    state.cols = snap.cols;
    state.rows = snap.rows;
    state.cells = snap.cells.slice();
    el.cols.value = state.cols;
    el.rows.value = state.rows;
  }

  function pushHistory() {
    state.undo.push(snapshot());
    if (state.undo.length > HISTORY_LIMIT) state.undo.shift();
    state.redo = [];
  }

  // ── rendering ────────────────────────────────────────────────────────────
  function buildGrid() {
    el.grid.style.setProperty('--ea-cols', state.cols);
    el.grid.style.setProperty('--ea-size', state.zoom + 'px');
    var frag = document.createDocumentFragment();
    for (var i = 0; i < state.cols * state.rows; i++) {
      var cell = document.createElement('div');
      cell.className = 'ea-cell';
      cell.dataset.i = i;
      cell.textContent = state.cells[i];
      frag.appendChild(cell);
    }
    el.grid.innerHTML = '';
    el.grid.appendChild(frag);
  }

  function paintCell(i) {
    var cell = el.grid.children[i];
    if (cell) cell.textContent = state.cells[i];
  }

  function setBrush(g) {
    var first = graphemes(g).filter(function (x) { return !isBlank(x); })[0];
    if (!first) return;
    state.brush = first;
    el.brush.textContent = first;
    if (state.tool === 'erase') selectTool('draw');
  }

  // ── tools ────────────────────────────────────────────────────────────────
  function selectTool(name) {
    state.tool = name;
    document.querySelectorAll('[data-ea-tool]').forEach(function (b) {
      b.classList.toggle('active', b.dataset.eaTool === name);
      b.setAttribute('aria-pressed', b.dataset.eaTool === name ? 'true' : 'false');
    });
  }

  function flood(start, value) {
    var target = state.cells[start];
    if (target === value) return;
    var stack = [start];
    while (stack.length) {
      var i = stack.pop();
      if (state.cells[i] !== target) continue;
      state.cells[i] = value;
      var x = i % state.cols, y = (i - x) / state.cols;
      if (x > 0) stack.push(i - 1);
      if (x < state.cols - 1) stack.push(i + 1);
      if (y > 0) stack.push(i - state.cols);
      if (y < state.rows - 1) stack.push(i + state.cols);
    }
    buildGrid();
  }

  function applyAt(i, ctrl) {
    if (ctrl) {                       // Ctrl/Cmd + click picks up the emoji under the cursor
      if (state.cells[i]) setBrush(state.cells[i]);
      return;
    }
    if (state.tool === 'draw') {
      if (state.cells[i] !== state.brush) { state.cells[i] = state.brush; paintCell(i); }
    } else if (state.tool === 'erase') {
      if (state.cells[i] !== '') { state.cells[i] = ''; paintCell(i); }
    }
  }

  function cellFromPoint(x, y) {
    var node = document.elementFromPoint(x, y);
    if (!node || !node.classList || !node.classList.contains('ea-cell')) return -1;
    return Number(node.dataset.i);
  }

  var dragging = false;

  el.grid.addEventListener('pointerdown', function (e) {
    var i = cellFromPoint(e.clientX, e.clientY);
    if (i < 0) return;
    e.preventDefault();
    var ctrl = e.ctrlKey || e.metaKey;
    if (ctrl) { applyAt(i, true); return; }
    pushHistory();
    if (state.tool === 'fill') {
      flood(i, state.brush);
      return;
    }
    dragging = true;
    applyAt(i, false);
    el.grid.setPointerCapture(e.pointerId);
  });

  el.grid.addEventListener('pointermove', function (e) {
    if (!dragging) return;
    var i = cellFromPoint(e.clientX, e.clientY);
    if (i >= 0) applyAt(i, false);
  });

  function stopDrag() { dragging = false; }
  el.grid.addEventListener('pointerup', stopDrag);
  el.grid.addEventListener('pointercancel', stopDrag);

  // ── actions ──────────────────────────────────────────────────────────────
  function undo() {
    if (!state.undo.length) return say('Nothing to undo.');
    state.redo.push(snapshot());
    restore(state.undo.pop());
    buildGrid();
  }

  function redo() {
    if (!state.redo.length) return say('Nothing to redo.');
    state.undo.push(snapshot());
    restore(state.redo.pop());
    buildGrid();
  }

  function clearAll() {
    pushHistory();
    state.cells = emptyCells(state.cols * state.rows);
    buildGrid();
  }

  function resize(cols, rows) {
    cols = clamp(Math.round(cols) || state.cols, MIN_SIZE, MAX_SIZE);
    rows = clamp(Math.round(rows) || state.rows, MIN_SIZE, MAX_SIZE);
    if (cols === state.cols && rows === state.rows) { el.cols.value = cols; el.rows.value = rows; return; }
    pushHistory();
    var next = emptyCells(cols * rows);
    for (var y = 0; y < Math.min(rows, state.rows); y++) {
      for (var x = 0; x < Math.min(cols, state.cols); x++) {
        next[y * cols + x] = state.cells[y * state.cols + x];
      }
    }
    state.cols = cols;
    state.rows = rows;
    state.cells = next;
    el.cols.value = cols;
    el.rows.value = rows;
    buildGrid();
  }

  function cropToFit() {
    var minX = state.cols, minY = state.rows, maxX = -1, maxY = -1;
    for (var i = 0; i < state.cells.length; i++) {
      if (!state.cells[i]) continue;
      var x = i % state.cols, y = (i - x) / state.cols;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    if (maxX < 0) return say('Draw something first, then crop.');
    var cols = Math.max(MIN_SIZE, maxX - minX + 1), rows = Math.max(MIN_SIZE, maxY - minY + 1);
    pushHistory();
    var next = emptyCells(cols * rows);
    for (var yy = minY; yy <= maxY; yy++) {
      for (var xx = minX; xx <= maxX; xx++) {
        next[(yy - minY) * cols + (xx - minX)] = state.cells[yy * state.cols + xx];
      }
    }
    state.cols = cols;
    state.rows = rows;
    state.cells = next;
    el.cols.value = cols;
    el.rows.value = rows;
    buildGrid();
    say('Cropped to the drawing.');
  }

  function addPadding() {
    var cols = state.cols + 2, rows = state.rows + 2;
    if (cols > MAX_SIZE || rows > MAX_SIZE) return say('The grid is already at its maximum size.');
    pushHistory();
    var next = emptyCells(cols * rows);
    for (var y = 0; y < state.rows; y++) {
      for (var x = 0; x < state.cols; x++) {
        next[(y + 1) * cols + (x + 1)] = state.cells[y * state.cols + x];
      }
    }
    state.cols = cols;
    state.rows = rows;
    state.cells = next;
    el.cols.value = cols;
    el.rows.value = rows;
    buildGrid();
  }

  function zoom(delta) {
    state.zoom = clamp(state.zoom + delta, 14, 56);
    el.grid.style.setProperty('--ea-size', state.zoom + 'px');
  }

  // ── output ───────────────────────────────────────────────────────────────
  function toText() {
    var blank = el.emptyChar.value;
    var lines = [];
    for (var y = 0; y < state.rows; y++) {
      var line = '';
      for (var x = 0; x < state.cols; x++) line += state.cells[y * state.cols + x] || blank;
      lines.push(line);
    }
    return lines.join('\n');
  }

  function copyText(text, done) {
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
      document.body.removeChild(ta);
      done(ok);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { done(true); }).catch(fallback);
    } else {
      fallback();
    }
  }

  function copyArt() {
    if (!state.cells.some(Boolean)) return say('Draw something first, then copy.');
    copyText(toText(), function (ok) {
      say(ok ? 'Copied! Paste it anywhere.' : 'Copy failed. Select the text from Download .txt instead.');
      if (ok && window.showToast) window.showToast('Emoji art copied ✓', '🎨');
    });
  }

  function download(filename, blob) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function downloadTxt() {
    if (!state.cells.some(Boolean)) return say('Draw something first.');
    download('emoji-art.txt', new Blob([toText()], { type: 'text/plain;charset=utf-8' }));
  }

  function downloadPng() {
    if (!state.cells.some(Boolean)) return say('Draw something first.');
    var size = 48;
    var canvas = document.createElement('canvas');
    canvas.width = state.cols * size;
    canvas.height = state.rows * size;
    var ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.font = Math.round(size * 0.78) + 'px "Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (var i = 0; i < state.cells.length; i++) {
      if (!state.cells[i]) continue;
      var x = i % state.cols, y = (i - x) / state.cols;
      ctx.fillText(state.cells[i], x * size + size / 2, y * size + size / 2 + 2);
    }
    canvas.toBlob(function (blob) { if (blob) download('emoji-art.png', blob); }, 'image/png');
  }

  // ── import ───────────────────────────────────────────────────────────────
  // The empty-cell characters the picker offers. Pasted art that is mostly one of them uses it as its background.
  function detectBackground(rows) {
    var total = 0, counts = {};
    rows.forEach(function (row) {
      row.forEach(function (g) { total++; counts[g] = (counts[g] || 0) + 1; });
    });
    var best = null;
    Array.prototype.forEach.call(el.emptyChar.options, function (option) {
      var n = counts[option.value] || 0;
      if (n && n * 4 >= total && (best === null || n > counts[best])) best = option.value;
    });
    return best;
  }

  function importText(text) {
    var lines = String(text).replace(/\r\n?/g, '\n').split('\n');
    while (lines.length && !lines[lines.length - 1].trim()) lines.pop();
    if (!lines.length) return say('Paste some emoji art first.');
    var rows = lines.map(function (line) { return graphemes(line); });
    // Cells equal to the background copy back as the same character, so treating them as empty loses nothing.
    var background = detectBackground(rows);
    if (background !== null) el.emptyChar.value = background;
    var blank = el.emptyChar.value;
    var cols = Math.max.apply(null, rows.map(function (r) { return r.length; }));
    if (cols > MAX_SIZE || rows.length > MAX_SIZE) {
      return say('That art is larger than ' + MAX_SIZE + ' by ' + MAX_SIZE + ' cells, so it cannot be imported.');
    }
    pushHistory();
    cols = Math.max(cols, MIN_SIZE);
    var height = Math.max(rows.length, MIN_SIZE);
    var cells = emptyCells(cols * height);
    rows.forEach(function (row, y) {
      row.forEach(function (g, x) { cells[y * cols + x] = (isBlank(g) || g === blank) ? '' : g; });
    });
    state.cols = cols;
    state.rows = height;
    state.cells = cells;
    el.cols.value = cols;
    el.rows.value = height;
    buildGrid();
    el.importBox.hidden = true;
    say('Imported.');
  }

  // ── palette ──────────────────────────────────────────────────────────────
  function showGroup(name) {
    el.palette.innerHTML = '';
    PALETTE[name].forEach(function (emoji) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'ea-pick';
      b.textContent = emoji;
      b.setAttribute('aria-label', 'Use ' + emoji);
      b.dataset.emoji = emoji;
      el.palette.appendChild(b);
    });
    el.tabs.querySelectorAll('button').forEach(function (t) {
      t.classList.toggle('active', t.dataset.group === name);
    });
  }

  function buildTabs() {
    Object.keys(PALETTE).forEach(function (name, idx) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'combo-filter__btn' + (idx === 0 ? ' active' : '');
      b.textContent = name;
      b.dataset.group = name;
      el.tabs.appendChild(b);
    });
    el.tabs.addEventListener('click', function (e) {
      var t = e.target.closest('button');
      if (t) showGroup(t.dataset.group);
    });
    el.palette.addEventListener('click', function (e) {
      var b = e.target.closest('.ea-pick');
      if (b) setBrush(b.dataset.emoji);
    });
  }

  // ── wiring ───────────────────────────────────────────────────────────────
  document.querySelectorAll('[data-ea-tool]').forEach(function (b) {
    b.addEventListener('click', function () { selectTool(b.dataset.eaTool); });
  });

  var actions = {
    undo: undo, redo: redo, clear: clearAll, crop: cropToFit, pad: addPadding,
    'zoom-in': function () { zoom(4); }, 'zoom-out': function () { zoom(-4); },
    copy: copyArt, txt: downloadTxt, png: downloadPng,
    import: function () { el.importBox.hidden = !el.importBox.hidden; if (!el.importBox.hidden) el.importText.focus(); },
    'import-apply': function () { importText(el.importText.value); },
    'import-close': function () { el.importBox.hidden = true; }
  };
  document.querySelectorAll('[data-ea-action]').forEach(function (b) {
    b.addEventListener('click', function () {
      var fn = actions[b.dataset.eaAction];
      if (fn) fn();
    });
  });

  el.custom.addEventListener('input', function () {
    if (el.custom.value) { setBrush(el.custom.value); }
  });
  el.cols.addEventListener('change', function () { resize(Number(el.cols.value), state.rows); });
  el.rows.addEventListener('change', function () { resize(state.cols, Number(el.rows.value)); });
  el.emptyChar.addEventListener('change', function () { say('Empty cells will copy as ' + (el.emptyChar.value === '　' ? 'a wide space' : el.emptyChar.value) + '.'); });

  el.file.addEventListener('change', function () {
    var f = el.file.files && el.file.files[0];
    if (!f) return;
    if (f.size > 200000) { say('That file is too large. Paste the text instead.'); el.file.value = ''; return; }
    var reader = new FileReader();
    reader.onload = function () { importText(String(reader.result)); el.file.value = ''; };
    reader.readAsText(f);
  });

  document.addEventListener('keydown', function (e) {
    var tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
    var mod = e.ctrlKey || e.metaKey;
    if (mod && !e.shiftKey && e.key.toLowerCase() === 'z') { e.preventDefault(); undo(); }
    else if (mod && (e.key.toLowerCase() === 'y' || (e.shiftKey && e.key.toLowerCase() === 'z'))) { e.preventDefault(); redo(); }
  });

  // ── start ────────────────────────────────────────────────────────────────
  state.cells = emptyCells(state.cols * state.rows);
  buildTabs();
  showGroup(Object.keys(PALETTE)[0]);
  el.brush.textContent = state.brush;
  selectTool('draw');
  buildGrid();
})();
