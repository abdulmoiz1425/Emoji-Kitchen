/* ════════════════════════════════════════════════════════════════════
   Emoji Kitchen — main.js
   Handles: picker, combo lookup, download, copy, surprise, animations
════════════════════════════════════════════════════════════════════ */
'use strict';

// ── Emoji dataset ──────────────────────────────────────────────────────────
const EMOJI_DATA = {
  'Smileys': [
    '😀','😃','😄','😁','😆','😅','🤣','😂','🙂','🙃','😉','😊','😇',
    '🥰','😍','🤩','😘','😗','😋','😛','😜','🤪','😝','🤑','🤗','🤔',
    '🤐','🤨','😐','😑','😶','😏','😒','🙄','😬','🤥','😌','😔','😪',
    '😴','😷','🤒','🤕','🤢','🤮','🤧','🥵','🥶','🥴','😵','🤯','🤠',
    '🥳','🥸','😎','🤓','🧐','😕','😟','🙁','☹️','😮','😯','😲','😳',
    '🥺','😦','😧','😨','😰','😥','😢','😭','😱','😖','😣','😞','😓',
    '😩','😫','😤','😡','😠','🤬','😈','👿','💀','☠️','💩','🤡','👻',
    '👽','🤖','👹','👺',
  ],
  'Hearts': [
    '❤️','🧡','💛','💚','💙','💜','🖤','🤍','🤎','💔','❤️‍🔥','❤️‍🩹',
    '💕','💞','💓','💗','💖','💘','💝','💟','♥️','💌','💋','🫀',
  ],
  'Animals': [
    '🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷',
    '🐸','🐵','🙈','🙉','🙊','🐔','🐧','🐦','🐤','🦆','🦅','🦉','🦇',
    '🐺','🐗','🐴','🦄','🐝','🐛','🦋','🐌','🐞','🐜','🦟','🦗','🕷️',
    '🦂','🐢','🐍','🦎','🐙','🦑','🦐','🦞','🦀','🐡','🐟','🐠','🐬',
    '🐳','🐋','🦈','🦭','🐊','🐅','🐆','🦓','🦍','🦧','🦣','🐘','🦛',
    '🦏','🐪','🐫','🦒','🦘','🦬','🐃','🐂','🐄','🐎','🐖','🐏','🐑',
    '🦙','🐐','🦌','🐕','🐩','🐈','🐓','🦃','🦤','🦚','🦜','🦢','🦩',
    '🕊️','🐇','🦝','🦨','🦡','🦫','🦦','🦥','🐁','🐀','🐿️','🦔',
  ],
  'Food': [
    '🍎','🍊','🍋','🍇','🍓','🫐','🍈','🍒','🍑','🥭','🍍','🥥','🥝',
    '🍅','🍆','🥑','🥦','🥬','🥒','🌶️','🧄','🧅','🥔','🥐','🥯','🍞',
    '🥖','🧀','🥚','🍳','🧈','🥞','🧇','🥓','🥩','🍗','🍖','🌮','🌯',
    '🥙','🍕','🍔','🍟','🌭','🥗','🍿','🍦','🍧','🍨','🍩','🍪','🎂',
    '🍰','🧁','🍫','🍬','🍭','🍮','🍯','🍡','🍣','🍙','🍚','🍛','🍜',
    '🍝','☕','🍵','🫖','🍺','🍻','🥂','🍷','🍸','🍹','🧃','🥤','🧋',
    '🍾','🧉','🫗',
  ],
  'Nature': [
    '🌲','🌳','🌴','🪵','🌱','🌿','☘️','🍀','🎍','🎋','🍃','🍂','🍁',
    '🌾','💐','🌷','🌹','🥀','🌺','🌸','🌼','🌻','🌞','🌝','🌛','🌜',
    '🌚','🌕','🌖','🌗','🌘','🌑','🌒','🌓','🌔','🌙','🌟','⭐','🌠',
    '🌌','☀️','🌤️','⛅','🌥️','☁️','🌦️','🌧️','⛈️','🌩️','🌨️','❄️',
    '☃️','⛄','🌬️','💨','🌪️','🌫️','🌈','☔','⚡','🔥','💧','🌊',
    '🌍','🌎','🌏','🗻','🏔️','🌋','🏝️','🏖️',
  ],
  'Activities': [
    '⚽','🏀','🏈','⚾','🥎','🎾','🏐','🏉','🎱','🏓','🏸','🥊','🥋',
    '🎯','🎣','🤿','🎿','⛷️','🏂','⛸️','🥌','🎭','🎨','🎤','🎧','🎼',
    '🎹','🥁','🪘','🎷','🎺','🎸','🪕','🎻','🎬','🎮','🕹️','🎲','♟️',
    '🧩','🧸','🪅','🪩','🪆','🎈','🎉','🎊','🎁','🎀','🎗️','🎟️','🎫',
  ],
  'Travel': [
    '🚗','🚕','🚙','🚌','🏎️','🚓','🚑','🚒','🚐','🛻','🚚','🚛','🚜',
    '🏍️','🛵','🚲','🛴','🛹','🚁','🛸','✈️','🛩️','🚀','🛶','⛵','🚢',
    '⛴️','🚂','🚄','🚅','🚇','🚊','🚞','🏠','🏡','🏢','🏥','🏦','🏨',
    '🏪','🏫','⛪','🕌','🛕','🗼','🗽','🗿','🏰','🏯','🎡','🎢','🎠',
  ],
  'Objects': [
    '💡','🔦','🕯️','💰','💎','⚖️','🔧','🪛','🔨','⛏️','⚒️','🛠️',
    '🔑','🗝️','🔐','🔒','🔓','🚪','🪑','🛋️','🛏️','🛁','🧴','🧹',
    '🧺','🧻','🧼','🪣','🧲','🪜','🧰','📱','💻','🖥️','⌨️','🖱️',
    '📷','📸','🎥','📞','☎️','📺','📻','🧭','⏱️','⏰','🔋','🔌',
    '📚','📖','📝','✏️','✂️','📦','📫','🎁','🔬','🔭','🩺','💊',
    '🩹','🧪','🧬','💉','🩸',
  ],
  'Symbols': [
    '✅','❌','⭕','🔴','🟠','🟡','🟢','🔵','🟣','⚫','⚪','🟤',
    '🔶','🔷','🔸','🔹','🔺','🔻','💠','🔘','🔲','🔳','▪️','▫️',
    '⬛','⬜','🏁','🚩','🎌','🏴','🏳️','⚡','💥','✨','🌟','💫',
    '🔔','🔕','🎵','🎶','💯','🆒','🆓','🆕','🆙','🆗','🆘','🔞',
    '⚠️','☢️','☣️','🚫','🔞','📵','🚷','🚯','🚳','🚱','🔇','📴',
    '✔️','💠','🔱','⚜️','🔰','♻️','✳️','❇️','🆚','💲','💱','🏧',
  ],
};

const ALL_EMOJIS = Object.entries(EMOJI_DATA).flatMap(([cat, list]) =>
  list.map(e => ({ emoji: e, category: cat }))
);

// Extended name map for search
const EMOJI_NAMES = {
  '😀':'grinning happy','😂':'joy laugh crying','🥰':'love smiling hearts',
  '😍':'heart eyes love','😎':'cool sunglasses','😭':'crying sob',
  '😱':'screaming fear shocked','🤔':'thinking hmm','😴':'sleeping tired',
  '🤗':'hugging face','😇':'angel halo','🥳':'party celebration',
  '🐱':'cat kitty','🐶':'dog puppy','🐻':'bear','🦊':'fox','🐼':'panda',
  '🦁':'lion','🐸':'frog','🐨':'koala','🐯':'tiger','🐮':'cow',
  '🦄':'unicorn','🐙':'octopus','🦋':'butterfly','🐝':'bee',
  '🔥':'fire flame hot','❤️':'heart love red','💛':'heart yellow',
  '💚':'heart green','💙':'heart blue','💜':'heart purple','🖤':'heart black',
  '🍕':'pizza','🍔':'burger hamburger','🍟':'fries','☕':'coffee hot',
  '🍰':'cake slice','🎂':'birthday cake','🍩':'donut','🍪':'cookie',
  '⭐':'star','🌟':'glowing star','🌈':'rainbow','❄️':'snowflake cold ice',
  '🔥':'fire','💧':'water drop','🌊':'wave ocean','⚡':'lightning bolt',
  '🎉':'party tada confetti','🎊':'confetti','🎈':'balloon',
  '🎁':'gift present','🎀':'ribbon bow',
  '🚗':'car vehicle','✈️':'airplane plane fly','🚀':'rocket space',
  '🛸':'ufo flying saucer','🏠':'house home',
  '💡':'light bulb idea','🔑':'key','📱':'phone mobile',
  '💻':'laptop computer','📚':'books study',
  '🌸':'cherry blossom flower','🌺':'hibiscus flower',
  '🌻':'sunflower','🌷':'tulip','🌹':'rose',
};

// Recent emojis (persisted in sessionStorage)
const RECENT_KEY = 'ek_recent';
function getRecent() {
  try { return JSON.parse(sessionStorage.getItem(RECENT_KEY)) || []; }
  catch { return []; }
}
function addToRecent(emoji) {
  const list = getRecent().filter(e => e !== emoji);
  list.unshift(emoji);
  sessionStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, 16)));
}

// ── My Combos — localStorage persistence ──────────────────────────────────
const COMBOS_KEY = 'ek_my_combos';

function getCombos() {
  try { return JSON.parse(localStorage.getItem(COMBOS_KEY)) || []; }
  catch { return []; }
}

function persistCombos(list) {
  localStorage.setItem(COMBOS_KEY, JSON.stringify(list));
}

function saveCombo(emoji1, emoji2, url) {
  const combos = getCombos();
  // Skip duplicates (either order)
  const isDupe = combos.some(c =>
    (c.emoji1 === emoji1 && c.emoji2 === emoji2) ||
    (c.emoji1 === emoji2 && c.emoji2 === emoji1)
  );
  if (isDupe) return;
  combos.unshift({ emoji1, emoji2, url, savedAt: Date.now() });
  persistCombos(combos.slice(0, 60)); // cap at 60 saved combos
  renderCombos();
}

function removeCombo(idx) {
  const combos = getCombos();
  combos.splice(idx, 1);
  persistCombos(combos);
  renderCombos();
}

function clearAllCombos() {
  localStorage.removeItem(COMBOS_KEY);
  renderCombos();
}

function loadSavedCombo(combo) {
  // Restore emojis into slots
  slot1Emoji = combo.emoji1; slot1EmojiEl.textContent = combo.emoji1; slot1Btn.classList.add('has-emoji');
  slot2Emoji = combo.emoji2; slot2EmojiEl.textContent = combo.emoji2; slot2Btn.classList.add('has-emoji');
  // Show image immediately — no need to re-cook
  comboUrl = combo.url;
  resultImg.src = combo.url;
  resultImg.hidden = false;
  resultBox.classList.add('has-result');
  showState('result');
  btnCopy.disabled = false;
  btnDownload.disabled = false;
  // Scroll mixer into view and confirm
  document.getElementById('kitchen').scrollIntoView({ behavior: 'smooth', block: 'center' });
  window.showToast('Combo loaded into the mixer!', '🍳');
}

function renderCombos() {
  const combos  = getCombos();
  const wrapper  = document.getElementById('my-combos');
  const grid     = document.getElementById('combos-grid');
  const countEl  = document.getElementById('combos-count');

  wrapper.hidden = combos.length === 0;
  countEl.textContent = combos.length;
  grid.innerHTML = '';

  combos.forEach((combo, idx) => {
    const card = document.createElement('div');
    card.className = 'combo-card';
    card.setAttribute('title', `${combo.emoji1} + ${combo.emoji2} — click to reload`);

    card.innerHTML = `
      <button class="combo-card__del" aria-label="Remove combo" title="Remove">×</button>
      <div class="combo-card__img">
        <img src="${combo.url}" alt="${combo.emoji1}+${combo.emoji2} mashup"
             onerror="this.parentElement.innerHTML='<span style=font-size:1.8rem>😢</span>'" />
      </div>
      <div class="combo-card__sources">
        <span>${combo.emoji1}</span>
        <span class="plus">+</span>
        <span>${combo.emoji2}</span>
      </div>
    `;

    // Click card body → load combo
    card.addEventListener('click', e => {
      if (e.target.closest('.combo-card__del')) return;
      loadSavedCombo(combo);
    });

    // Click × → animate out then remove
    card.querySelector('.combo-card__del').addEventListener('click', e => {
      e.stopPropagation();
      card.classList.add('removing');
      card.addEventListener('animationend', () => removeCombo(idx), { once: true });
    });

    grid.appendChild(card);
  });
}

// ── State ─────────────────────────────────────────────────────────────────
let activeSlot = null;
let slot1Emoji = '';
let slot2Emoji = '';
let comboUrl   = '';
let activeTab  = 'Smileys';

// ── DOM refs ──────────────────────────────────────────────────────────────
const overlay      = document.getElementById('picker-overlay');
const pickerClose  = document.getElementById('picker-close');
const emojiSearch  = document.getElementById('emoji-search');
const pickerTabs   = document.getElementById('picker-tabs');
const pickerGrid   = document.getElementById('picker-grid');

const slot1Btn     = document.getElementById('slot1');
const slot2Btn     = document.getElementById('slot2');
const slot1EmojiEl = document.getElementById('slot1-emoji');
const slot2EmojiEl = document.getElementById('slot2-emoji');

const resultBox    = document.getElementById('mixer-result');
const resultImg    = document.getElementById('result-img');
const resultPlaceholder = document.getElementById('result-placeholder');
const resultLoading = document.getElementById('result-loading');
const resultError  = document.getElementById('result-error');

const btnSurprise  = document.getElementById('btn-surprise');
const btnReset     = document.getElementById('btn-reset');
const btnCopy      = document.getElementById('btn-copy');
const btnDownload  = document.getElementById('btn-download');

// ── Picker open/close ─────────────────────────────────────────────────────
function openPicker(slot) {
  activeSlot = slot;
  emojiSearch.value = '';
  renderTabs();
  renderGrid(getTabEmojis(activeTab));
  overlay.hidden = false;
  document.body.style.overflow = 'hidden';
  setTimeout(() => emojiSearch.focus(), 60);
}

function closePicker() {
  overlay.hidden = true;
  activeSlot = null;
  document.body.style.overflow = '';
}

slot1Btn.addEventListener('click', () => openPicker(1));
slot2Btn.addEventListener('click', () => openPicker(2));
pickerClose.addEventListener('click', closePicker);
overlay.addEventListener('click', e => { if (e.target === overlay) closePicker(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closePicker(); });

// ── Tabs ──────────────────────────────────────────────────────────────────
const ALL_TABS = ['Recent', ...Object.keys(EMOJI_DATA)];

function getTabEmojis(tab) {
  if (tab === 'Recent') return getRecent();
  return EMOJI_DATA[tab] || [];
}

function renderTabs() {
  pickerTabs.innerHTML = '';
  ALL_TABS.forEach(tab => {
    if (tab === 'Recent' && getRecent().length === 0) return;
    const btn = document.createElement('button');
    btn.className = 'picker__tab' + (tab === activeTab ? ' active' : '');
    btn.textContent = tab === 'Recent' ? '🕐 Recent' : tab;
    btn.setAttribute('role', 'tab');
    btn.addEventListener('click', () => {
      activeTab = tab;
      emojiSearch.value = '';
      renderTabs();
      renderGrid(getTabEmojis(tab));
    });
    pickerTabs.appendChild(btn);
  });
}

// ── Emoji grid ────────────────────────────────────────────────────────────
function renderGrid(emojis) {
  pickerGrid.innerHTML = '';

  if (emojis.length === 0) {
    const msg = document.createElement('p');
    msg.className = 'picker__empty';
    const isRecent = activeTab === 'Recent';
    msg.textContent = isRecent
      ? 'No recent emojis yet — pick one!'
      : 'No emojis match your search.';
    pickerGrid.appendChild(msg);
    return;
  }

  const frag = document.createDocumentFragment();
  emojis.forEach(item => {
    const em = typeof item === 'string' ? item : item.emoji;
    const btn = document.createElement('button');
    btn.className = 'picker__emoji';
    btn.textContent = em;
    btn.setAttribute('role', 'option');
    btn.title = EMOJI_NAMES[em] || em;
    btn.addEventListener('click', () => selectEmoji(em));
    frag.appendChild(btn);
  });
  pickerGrid.appendChild(frag);
}

// ── Search ────────────────────────────────────────────────────────────────
emojiSearch.addEventListener('input', () => {
  const q = emojiSearch.value.trim().toLowerCase();
  if (!q) { renderGrid(getTabEmojis(activeTab)); return; }
  const results = ALL_EMOJIS
    .filter(({ emoji }) => emoji.includes(q) || (EMOJI_NAMES[emoji] || '').includes(q))
    .map(({ emoji }) => emoji);
  renderGrid(results);
});

// ── Select emoji ──────────────────────────────────────────────────────────
function selectEmoji(emoji) {
  addToRecent(emoji);

  if (activeSlot === 1) {
    slot1Emoji = emoji;
    slot1EmojiEl.textContent = emoji;
    slot1Btn.classList.add('has-emoji');
  } else {
    slot2Emoji = emoji;
    slot2EmojiEl.textContent = emoji;
    slot2Btn.classList.add('has-emoji');
  }

  // Slot pop animation
  const btn = activeSlot === 1 ? slot1Btn : slot2Btn;
  btn.animate([
    { transform:'scale(1.25)' },
    { transform:'scale(.92)' },
    { transform:'scale(1)' },
  ], { duration: 320, easing:'ease-out' });

  closePicker();
  if (slot1Emoji && slot2Emoji) cookCombo();
}

// ── Cook combo ────────────────────────────────────────────────────────────
async function cookCombo() {
  showState('loading');
  comboUrl = '';
  btnCopy.disabled = true;
  btnDownload.disabled = true;

  try {
    const params = new URLSearchParams({ emoji1: slot1Emoji, emoji2: slot2Emoji });
    const res = await fetch(`/api/combo/?${params}`);
    if (!res.ok) throw new Error('API error');
    const data = await res.json();

    const validUrl = await findValidImage(data.urls || []);
    if (validUrl) {
      comboUrl = validUrl;
      resultImg.src = validUrl;
      resultImg.hidden = false;
      resultBox.classList.add('has-result');
      showState('result');
      btnCopy.disabled = false;
      btnDownload.disabled = false;
      // Auto-save to My Combos
      const isNew = !getCombos().some(c =>
        (c.emoji1 === slot1Emoji && c.emoji2 === slot2Emoji) ||
        (c.emoji1 === slot2Emoji && c.emoji2 === slot1Emoji)
      );
      saveCombo(slot1Emoji, slot2Emoji, validUrl);
      if (isNew) window.showToast('Saved to My Combos!', '⭐');
    } else {
      showState('error');
      window.showToast("Combo not found — try another pair!", '😕', true);
    }
  } catch (err) {
    console.error(err);
    showState('error');
    window.showToast("Something went wrong. Please try again.", '⚠️', true);
  }
}

function findValidImage(urls) {
  return new Promise(resolve => {
    let idx = 0;
    function tryNext() {
      if (idx >= urls.length) { resolve(null); return; }
      const url = urls[idx++];
      const img = new Image();
      img.onload  = () => resolve(url);
      img.onerror = tryNext;
      img.src = url;
    }
    tryNext();
  });
}

function showState(state) {
  resultPlaceholder.hidden = true;
  resultLoading.hidden     = true;
  resultImg.hidden         = true;
  resultError.hidden       = true;
  resultBox.classList.remove('has-result');

  if (state === 'loading') resultLoading.hidden = false;
  if (state === 'error')   resultError.hidden   = false;
  if (state === 'idle')    resultPlaceholder.hidden = false;
  // 'result': resultImg shown above, has-result set above
}

// ── Surprise me ───────────────────────────────────────────────────────────
btnSurprise.addEventListener('click', () => {
  const all = ALL_EMOJIS.map(e => e.emoji);
  const e1  = all[Math.floor(Math.random() * all.length)];
  let e2;
  do { e2 = all[Math.floor(Math.random() * all.length)]; } while (e2 === e1);

  slot1Emoji = e1; slot1EmojiEl.textContent = e1; slot1Btn.classList.add('has-emoji');
  slot2Emoji = e2; slot2EmojiEl.textContent = e2; slot2Btn.classList.add('has-emoji');

  // Wiggle both slots
  [slot1Btn, slot2Btn].forEach((btn, i) => {
    setTimeout(() => {
      btn.animate([
        {transform:'rotate(-6deg) scale(1.15)'},
        {transform:'rotate(6deg)  scale(1.15)'},
        {transform:'rotate(0)     scale(1)'},
      ], {duration:400, easing:'ease-out'});
    }, i * 80);
  });

  cookCombo();
});

// ── Reset ─────────────────────────────────────────────────────────────────
btnReset.addEventListener('click', () => {
  slot1Emoji = ''; slot1EmojiEl.textContent = ''; slot1Btn.classList.remove('has-emoji');
  slot2Emoji = ''; slot2EmojiEl.textContent = ''; slot2Btn.classList.remove('has-emoji');
  comboUrl = '';
  resultImg.src = ''; resultImg.hidden = true;
  btnCopy.disabled = true; btnDownload.disabled = true;
  showState('idle');
});

// ── Download ──────────────────────────────────────────────────────────────
btnDownload.addEventListener('click', () => {
  if (!comboUrl) return;
  const link = document.createElement('a');
  link.href     = `/api/download/?url=${encodeURIComponent(comboUrl)}`;
  link.download = 'emoji_mashup.png';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.showToast('Downloading your mashup!', '⬇️');
});

// ── Copy emojis as text ───────────────────────────────────────────────────
btnCopy.addEventListener('click', () => {
  if (!slot1Emoji || !slot2Emoji) return;
  const text = slot1Emoji + slot2Emoji;
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text)
      .then(() => window.showToast(`${text} copied — paste anywhere!`, '✅'))
      .catch(() => fallbackCopy(text));
  } else {
    fallbackCopy(text);
  }
});

function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
    window.showToast(`${text} copied — paste anywhere!`, '✅');
  } catch {
    window.showToast('Copy failed — try selecting the emojis manually', '⚠️', true);
  }
  document.body.removeChild(ta);
}

// ── Clear-all button ──────────────────────────────────────────────────────
document.getElementById('btn-clear-combos')?.addEventListener('click', () => {
  if (confirm('Remove all saved combos?')) {
    clearAllCombos();
    window.showToast('All combos cleared', '🗑️');
  }
});

// ── Init ──────────────────────────────────────────────────────────────────
renderTabs();
renderGrid(getTabEmojis(activeTab));
showState('idle');
renderCombos(); // restore saved combos from localStorage
