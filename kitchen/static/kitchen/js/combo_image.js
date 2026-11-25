/* Mood finder: copy a set as a picture, and copy or download a mashup image.
   - "Copy image" on a set draws the emojis onto a canvas in the browser and puts that picture on the clipboard.
   - Mashup cards copy or download the Emoji Kitchen image from the site's own image service.
   Browsers only allow image copying on https pages (and localhost). Where it is not allowed, a set is saved as a
   picture instead, and a mashup points to its Download button. The emojis are never copied as text by these buttons.
   Nothing the visitor typed is sent anywhere. Usage events carry only a fixed outcome word. */
(function () {
  'use strict';

  var EMOJI_FONT = '"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji","Twemoji Mozilla",sans-serif';
  var CELL = 120;          // px per emoji on the picture
  var PAD = 36;            // px around the emojis
  var PER_ROW = 6;

  function toast(message, icon, isError) {
    if (typeof window.showToast === 'function') window.showToast(message, icon, isError);
  }

  function track(action, outcome) {
    try {
      if (typeof window.gtag === 'function') window.gtag('event', 'combo_image_' + action, { outcome: outcome });
    } catch (err) { /* analytics must never break the page */ }
  }

  function canCopyImages() {
    return Boolean(navigator.clipboard && navigator.clipboard.write && window.ClipboardItem);
  }

  function saveBlob(blob, filename) {
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  // Split into visible emojis (a flag or a family is one emoji, not several characters).
  function splitEmojis(text) {
    var clean = String(text).replace(/\s+/g, '');
    if (typeof Intl !== 'undefined' && Intl.Segmenter) {
      return Array.from(new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(clean), function (s) { return s.segment; });
    }
    return Array.from(clean);
  }

  // Draw a set of emojis on a transparent canvas and give back a PNG.
  function drawCombo(text) {
    var items = splitEmojis(text).slice(0, 36);
    var cols = Math.max(1, Math.min(items.length, PER_ROW));
    var rows = Math.max(1, Math.ceil(items.length / PER_ROW));
    var canvas = document.createElement('canvas');
    canvas.width = PAD * 2 + cols * CELL;
    canvas.height = PAD * 2 + rows * CELL;
    var ctx = canvas.getContext('2d');
    ctx.font = Math.round(CELL * 0.8) + 'px ' + EMOJI_FONT;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    items.forEach(function (item, i) {
      var row = Math.floor(i / PER_ROW);
      var inRow = Math.min(PER_ROW, items.length - row * PER_ROW);
      var offset = (cols - inRow) * CELL / 2;                    // centre a short last row
      var x = PAD + offset + (i % PER_ROW) * CELL + CELL / 2;
      var y = PAD + row * CELL + CELL / 2 + CELL * 0.04;
      ctx.fillText(item, x, y);
    });
    return new Promise(function (resolve, reject) {
      canvas.toBlob(function (blob) { blob ? resolve(blob) : reject(new Error('Could not draw the image')); }, 'image/png');
    });
  }

  function busy(btn, label) {
    var original = btn.dataset.idleLabel || btn.textContent;
    btn.dataset.idleLabel = original;
    btn.disabled = true;
    btn.textContent = label;
    return function done(finalLabel) {
      btn.textContent = finalLabel || original;
      btn.disabled = false;
      if (finalLabel) setTimeout(function () { btn.textContent = original; }, 1800);
    };
  }

  // ── A set → picture ──
  async function copyComboImage(btn) {
    var combo = btn.dataset.comboImage;
    if (!combo) return;
    if (!canCopyImages()) {
      // Saving is the next best thing, so the visitor still ends up with a picture.
      var saving = busy(btn, 'Saving…');
      try {
        saveBlob(await drawCombo(combo), 'emoji-combo.png');
        toast(window.isSecureContext === false
          ? 'Copying an image needs a secure (https) page, so the image was saved instead.'
          : "This browser can't copy images, so the image was saved instead.", '⬇️', true);
        track('combo_copy', window.isSecureContext === false ? 'saved_needs_https' : 'saved_unsupported');
        saving('✅ Saved');
      } catch (err) {
        console.error(err);
        toast("Couldn't make the image.", '⚠️', true);
        track('combo_copy', 'failed');
        saving();
      }
      return;
    }
    var done = busy(btn, 'Copying…');
    try {
      // The promise is made inside the tap (Safari needs that) and the clipboard waits for it.
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': drawCombo(combo) })]);
      toast('Image copied. Paste it into a chat!', '✅');
      track('combo_copy', 'copied');
      done('✅ Copied!');
    } catch (err) {
      console.error('Image copy failed:', err);
      toast("Couldn't copy the image. Try again.", '⚠️', true);
      track('combo_copy', 'failed');
      done();
    }
  }

  // ── A mashup → picture ──
  async function fetchMashup(card, format) {
    var params = new URLSearchParams({ emoji1: card.dataset.emoji1, emoji2: card.dataset.emoji2, format: format });
    var holder = card.closest('[data-sticker-version]');
    if (holder && holder.dataset.stickerVersion) params.set('v', holder.dataset.stickerVersion);
    var res = await fetch('/api/sticker/?' + params);
    if (!res.ok) throw new Error('Image request failed (' + res.status + ')');
    return res.blob();
  }

  async function fetchPlainMashup(card) {
    var res = await fetch(card.dataset.image, { mode: 'cors' });
    if (!res.ok) throw new Error('Image fetch failed');
    return res.blob();
  }

  async function copyMashup(btn, card) {
    if (!canCopyImages()) {
      if (window.isSecureContext === false) {
        toast('Copying an image needs a secure (https) page. Use Download image instead.', '⚠️', true);
        track('mashup_copy', 'needs_https');
      } else {
        toast("This browser can't copy images. Use Download image instead.", '⚠️', true);
        track('mashup_copy', 'unsupported');
      }
      return;
    }
    var outcome = 'copied';
    var blob = fetchMashup(card, 'png').catch(function () {
      outcome = 'plain_image';
      return fetchPlainMashup(card);
    });
    var done = busy(btn, 'Copying…');
    try {
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
      toast('Image copied. Paste it into a chat!', '✅');
      track('mashup_copy', outcome);
      done('✅ Copied!');
    } catch (err) {
      console.error('Image copy failed:', err);
      toast("Couldn't copy the image. Use Download image instead.", '⚠️', true);
      track('mashup_copy', 'failed');
      done();
    }
  }

  async function downloadMashup(btn, card) {
    var done = busy(btn, 'Making image…');
    var name = 'emoji-kitchen-' + card.dataset.emoji1 + '-' + card.dataset.emoji2;
    try {
      saveBlob(await fetchMashup(card, 'webp'), name + '.webp');
      toast('Image saved!', '⬇️');
      track('mashup_download', 'webp');
      done('✅ Saved');
    } catch (err) {
      console.error('Image download failed, saving the plain image:', err);
      try {
        saveBlob(await fetchPlainMashup(card), name + '.png');
        toast('Image saved!', '⬇️');
        track('mashup_download', 'plain_image');
        done('✅ Saved');
      } catch (err2) {
        window.open(card.dataset.image, '_blank', 'noopener');
        toast('Opened the image. Long-press it to save.', '⬇️', true);
        track('mashup_download', 'opened');
        done();
      }
    }
  }

  document.addEventListener('click', function (e) {
    var comboBtn = e.target.closest('[data-combo-image]');
    if (comboBtn) { copyComboImage(comboBtn); return; }
    var mashBtn = e.target.closest('[data-mashup-action]');
    if (!mashBtn) return;
    var card = mashBtn.closest('.mood-mashup-card');
    if (!card) return;
    if (mashBtn.dataset.mashupAction === 'copy') copyMashup(mashBtn, card);
    else downloadMashup(mashBtn, card);
  });
})();
