/* Image to Dot Art Generator: turns a picture into Braille text art.
   The image is read and converted in the browser. It is never uploaded. */
(function () {
  'use strict';

  var root = document.getElementById('da-app');
  if (!root) return;

  var MAX_FILE_BYTES = 15 * 1024 * 1024;

  var el = {
    file: document.getElementById('da-file'),
    drop: document.getElementById('da-drop'),
    mode: document.getElementById('da-mode'),
    width: document.getElementById('da-width'),
    threshold: document.getElementById('da-threshold'),
    contrast: document.getElementById('da-contrast'),
    edge: document.getElementById('da-edge'),
    invert: document.getElementById('da-invert'),
    solid: document.getElementById('da-solid'),
    edgeRow: document.getElementById('da-edge-row'),
    thresholdRow: document.getElementById('da-threshold-row'),
    widthOut: document.getElementById('da-width-out'),
    thresholdOut: document.getElementById('da-threshold-out'),
    contrastOut: document.getElementById('da-contrast-out'),
    edgeOut: document.getElementById('da-edge-out'),
    generate: document.getElementById('da-generate'),
    status: document.getElementById('da-status'),
    results: document.getElementById('da-results'),
    output: document.getElementById('da-output'),
    meta: document.getElementById('da-meta'),
    preview: document.getElementById('da-preview'),
    copy: document.getElementById('da-copy'),
    txt: document.getElementById('da-txt'),
    full: document.getElementById('da-full')
  };

  var image = null;      // the decoded <img> / ImageBitmap source
  var lastText = '';

  function say(message, isError) {
    el.status.textContent = message || '';
    el.status.classList.toggle('da-status--error', !!isError);
  }

  // ── loading the picture ─────────────────────────────────────────────────
  function loadFile(file) {
    if (!file) return;
    if (!/^image\//.test(file.type)) return say('Please choose an image file (PNG, JPG, WebP or GIF).', true);
    if (file.size > MAX_FILE_BYTES) return say('That image is larger than 15 MB. Try a smaller one.', true);
    var url = URL.createObjectURL(file);
    var img = new Image();
    img.onload = function () {
      image = img;
      el.preview.src = url;
      el.preview.hidden = false;
      say('');
      generate();
    };
    img.onerror = function () {
      URL.revokeObjectURL(url);
      say('That file could not be read as an image.', true);
    };
    img.src = url;
  }

  // ── conversion ──────────────────────────────────────────────────────────
  function grayPixels(img, dotsWide) {
    var ratio = img.naturalHeight / img.naturalWidth;
    var w = dotsWide;
    var h = Math.max(4, Math.round(w * ratio / 4) * 4);   // multiple of 4 dots per braille row
    var canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    var ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.fillStyle = '#ffffff';                               // transparent areas become white
    ctx.fillRect(0, 0, w, h);
    ctx.drawImage(img, 0, 0, w, h);
    var data = ctx.getImageData(0, 0, w, h).data;
    var gray = new Float32Array(w * h);
    for (var i = 0, p = 0; i < gray.length; i++, p += 4) {
      gray[i] = 0.299 * data[p] + 0.587 * data[p + 1] + 0.114 * data[p + 2];
    }
    return { gray: gray, w: w, h: h };
  }

  function applyContrast(gray, amount) {
    if (!amount) return;
    var f = (259 * (amount + 255)) / (255 * (259 - amount));
    for (var i = 0; i < gray.length; i++) {
      var v = f * (gray[i] - 128) + 128;
      gray[i] = v < 0 ? 0 : v > 255 ? 255 : v;
    }
  }

  // Returns a Uint8Array of w*h: 1 where a dot should be raised.
  function toDots(px, mode, threshold, edgeLevel, invert) {
    var w = px.w, h = px.h, g = px.gray;
    var dots = new Uint8Array(w * h);
    var i, x, y;

    if (mode === 'threshold') {
      for (i = 0; i < dots.length; i++) dots[i] = g[i] < threshold ? 1 : 0;
    } else if (mode === 'dither') {
      var buf = Float32Array.from(g);
      for (y = 0; y < h; y++) {
        for (x = 0; x < w; x++) {
          i = y * w + x;
          var old = buf[i];
          var neu = old < threshold ? 0 : 255;
          dots[i] = neu === 0 ? 1 : 0;
          var err = old - neu;
          if (x + 1 < w) buf[i + 1] += err * 7 / 16;
          if (y + 1 < h) {
            if (x > 0) buf[i + w - 1] += err * 3 / 16;
            buf[i + w] += err * 5 / 16;
            if (x + 1 < w) buf[i + w + 1] += err * 1 / 16;
          }
        }
      }
    } else {                                                  // 'lines': Sobel edge detection
      var limit = 255 - edgeLevel;                            // higher slider = more lines
      for (y = 1; y < h - 1; y++) {
        for (x = 1; x < w - 1; x++) {
          i = y * w + x;
          var gx = -g[i - w - 1] - 2 * g[i - 1] - g[i + w - 1] + g[i - w + 1] + 2 * g[i + 1] + g[i + w + 1];
          var gy = -g[i - w - 1] - 2 * g[i - w] - g[i - w + 1] + g[i + w - 1] + 2 * g[i + w] + g[i + w + 1];
          dots[i] = Math.sqrt(gx * gx + gy * gy) > limit ? 1 : 0;
        }
      }
    }

    if (invert) for (i = 0; i < dots.length; i++) dots[i] ^= 1;
    return dots;
  }

  // Braille bit for each dot position inside a 2 wide by 4 tall cell.
  var BIT = [[0x01, 0x08], [0x02, 0x10], [0x04, 0x20], [0x40, 0x80]];

  function toBraille(dots, w, h, solid) {
    var lines = [];
    for (var cy = 0; cy < h; cy += 4) {
      var line = '';
      for (var cx = 0; cx < w; cx += 2) {
        var bits = 0;
        for (var dy = 0; dy < 4; dy++) {
          for (var dx = 0; dx < 2; dx++) {
            var x = cx + dx, y = cy + dy;
            if (x < w && y < h && dots[y * w + x]) bits |= BIT[dy][dx];
          }
        }
        // U+2800 is an empty cell that many apps collapse; U+2804 keeps the spacing.
        line += String.fromCharCode(0x2800 + (bits === 0 && solid ? 0x04 : bits));
      }
      lines.push(line);
    }
    return lines.join('\n');
  }

  function generate() {
    if (!image) return say('Choose an image first.', true);
    el.generate.disabled = true;
    say('Processing…');
    // Let the browser paint the message before the heavy loop runs.
    setTimeout(function () {
      try {
        var charsWide = Number(el.width.value);
        var px = grayPixels(image, charsWide * 2);
        applyContrast(px.gray, Number(el.contrast.value));
        var dots = toDots(px, el.mode.value, Number(el.threshold.value), Number(el.edge.value), el.invert.checked);
        lastText = toBraille(dots, px.w, px.h, el.solid.checked);
        el.output.textContent = lastText;
        el.meta.textContent = charsWide + ' characters wide, ' + lastText.split('\n').length + ' lines, ' +
          lastText.length.toLocaleString() + ' characters in total.';
        el.results.hidden = false;
        say('');
      } catch (err) {
        say('Something went wrong while converting that image. Try a smaller size.', true);
      }
      el.generate.disabled = false;
    }, 20);
  }

  // ── controls ────────────────────────────────────────────────────────────
  function syncLabels() {
    el.widthOut.textContent = el.width.value;
    el.thresholdOut.textContent = el.threshold.value;
    el.contrastOut.textContent = el.contrast.value;
    el.edgeOut.textContent = el.edge.value;
    var lines = el.mode.value === 'lines';
    el.edgeRow.hidden = !lines;
    el.thresholdRow.hidden = lines;
  }

  var pending = null;
  function regenerateSoon() {
    syncLabels();
    if (!image) return;
    clearTimeout(pending);
    pending = setTimeout(generate, 180);
  }

  [el.mode, el.width, el.threshold, el.contrast, el.edge, el.invert, el.solid].forEach(function (control) {
    control.addEventListener('input', regenerateSoon);
    control.addEventListener('change', regenerateSoon);
  });

  el.generate.addEventListener('click', generate);
  el.file.addEventListener('change', function () { loadFile(el.file.files && el.file.files[0]); });

  ['dragenter', 'dragover'].forEach(function (name) {
    el.drop.addEventListener(name, function (e) { e.preventDefault(); el.drop.classList.add('is-over'); });
  });
  ['dragleave', 'drop'].forEach(function (name) {
    el.drop.addEventListener(name, function (e) { e.preventDefault(); el.drop.classList.remove('is-over'); });
  });
  el.drop.addEventListener('drop', function (e) {
    var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    loadFile(file);
  });

  el.copy.addEventListener('click', function () {
    if (!lastText) return;
    function done(ok) {
      el.copy.textContent = ok ? '✅ Copied!' : 'Copy failed';
      setTimeout(function () { el.copy.textContent = '📋 Copy dot art'; }, 1800);
      if (ok && window.showToast) window.showToast('Dot art copied ✓', '⣿');
    }
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = lastText;
      ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
      document.body.removeChild(ta);
      done(ok);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(lastText).then(function () { done(true); }).catch(fallback);
    } else {
      fallback();
    }
  });

  el.txt.addEventListener('click', function () {
    if (!lastText) return;
    var url = URL.createObjectURL(new Blob([lastText], { type: 'text/plain;charset=utf-8' }));
    var a = document.createElement('a');
    a.href = url;
    a.download = 'dot-art.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });

  el.full.addEventListener('click', function () {
    var target = el.output.parentElement;
    if (target.requestFullscreen) target.requestFullscreen();
    else say('Fullscreen is not supported in this browser.', true);
  });

  syncLabels();
})();
