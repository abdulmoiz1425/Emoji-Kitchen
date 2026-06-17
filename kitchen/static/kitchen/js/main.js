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
  persistCombos(combos.slice(0, 6)); // cap at 6 saved combos
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
  compatibleEmojisSet = null; // no compat filter when restoring a saved result
  // Restore emojis into both pickers
  [[1, combo.emoji1], [2, combo.emoji2]].forEach(([panel, emoji]) => {
    setActiveTab(panel, categoryOf(emoji));
    setSlotEmoji(panel, emoji);
    PANELS[panel].search.value = '';
    renderTabs(panel);
    renderGrid(panel, getCurrentList(panel));
  });
  // Show image immediately — no need to re-cook
  comboUrl = combo.url;
  showState('result');           // switches to result-box, clears child states
  resultImg.src = combo.url;
  resultImg.style.display = '';
  resultBox.classList.add('has-result');
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
let slot1Emoji = '';
let slot2Emoji = '';
let comboUrl   = '';
let activeTab1 = 'All Emojis';
let activeTab2 = 'All Emojis';
// Set of emoji2 values that have a valid combo with the current slot1 emoji.
// null = no filter active (panel 2 shows all emojis enabled).
let compatibleEmojisSet = null;

// ── DOM refs ──────────────────────────────────────────────────────────────
const PANELS = {
  1: {
    search: document.getElementById('emoji-search-1'),
    tabs:   document.getElementById('picker-tabs-1'),
    grid:   document.getElementById('picker-grid-1'),
    chip:   document.getElementById('chip1'),
  },
  2: {
    search: document.getElementById('emoji-search-2'),
    tabs:   document.getElementById('picker-tabs-2'),
    grid:   document.getElementById('picker-grid-2'),
    chip:   document.getElementById('chip2'),
  },
};

const resultBox    = document.getElementById('mixer-result');
const resultImg    = document.getElementById('result-img');
const resultPlaceholder = document.getElementById('result-placeholder');
const resultLoading = document.getElementById('result-loading');
const resultError  = document.getElementById('result-error');

const comboGallery     = document.getElementById('combo-gallery');
const galleryLoadingEl = document.getElementById('combo-gallery-loading');
const comboGalleryGrid = document.getElementById('combo-gallery-grid');

const btnSurprise  = document.getElementById('btn-surprise');
const btnReset     = document.getElementById('btn-reset');
const btnCopy      = document.getElementById('btn-copy');
const btnDownload  = document.getElementById('btn-download');

// ── Tabs ──────────────────────────────────────────────────────────────────
const ALL_TABS = ['All Emojis', 'Recent', ...Object.keys(EMOJI_DATA)];

function getTabEmojis(tab) {
  if (tab === 'All Emojis') return ALL_EMOJIS;
  if (tab === 'Recent') return getRecent();
  return EMOJI_DATA[tab] || [];
}

function getActiveTab(panel) { return panel === 1 ? activeTab1 : activeTab2; }
function setActiveTab(panel, tab) { if (panel === 1) activeTab1 = tab; else activeTab2 = tab; }
function getSlotEmoji(panel) { return panel === 1 ? slot1Emoji : slot2Emoji; }

function categoryOf(emoji) {
  const found = ALL_EMOJIS.find(e => e.emoji === emoji);
  return found ? found.category : 'Smileys';
}

// Current list shown in a panel, honouring its search box / active tab
function getCurrentList(panel) {
  const q = PANELS[panel].search.value.trim().toLowerCase();
  if (!q) return getTabEmojis(getActiveTab(panel));
  return ALL_EMOJIS
    .filter(({ emoji }) => emoji.includes(q) || (EMOJI_NAMES[emoji] || '').includes(q))
    .map(({ emoji }) => emoji);
}

function renderTabs(panel) {
  const { tabs, search } = PANELS[panel];
  const activeTab = getActiveTab(panel);
  tabs.innerHTML = '';
  ALL_TABS.forEach(tab => {
    if (tab === 'Recent' && getRecent().length === 0) return;
    const btn = document.createElement('button');
    btn.className = 'picker__tab' + (tab === activeTab ? ' active' : '');
    btn.textContent = tab === 'All Emojis' ? '✨ All' : tab === 'Recent' ? '🕐 Recent' : tab;
    btn.setAttribute('role', 'tab');
    btn.addEventListener('click', () => {
      setActiveTab(panel, tab);
      search.value = '';
      renderTabs(panel);
      renderGrid(panel, getTabEmojis(tab));
    });
    tabs.appendChild(btn);
  });
}

// ── Emoji grid ────────────────────────────────────────────────────────────
function renderGrid(panel, emojis) {
  const { grid } = PANELS[panel];
  const selected = getSlotEmoji(panel);
  grid.innerHTML = '';

  if (emojis.length === 0) {
    const msg = document.createElement('p');
    msg.className = 'picker__empty';
    const isRecent = getActiveTab(panel) === 'Recent';
    msg.textContent = isRecent
      ? 'No recent emojis yet — pick one!'
      : 'No emojis match your search.';
    grid.appendChild(msg);
    return;
  }

  const frag = document.createDocumentFragment();
  emojis.forEach(item => {
    const em = typeof item === 'string' ? item : item.emoji;
    // Disable incompatible emojis in panel 2 once we know what's compatible
    const isDisabled = panel === 2 && compatibleEmojisSet !== null && !compatibleEmojisSet.has(em);

    const btn = document.createElement('button');
    let cls = 'picker__emoji';
    if (em === selected) cls += ' active';
    if (isDisabled)      cls += ' is-disabled';
    btn.className = cls;
    btn.textContent = em;
    btn.setAttribute('role', 'option');
    btn.title = EMOJI_NAMES[em] || em;

    if (isDisabled) {
      btn.disabled = true;
      btn.setAttribute('aria-disabled', 'true');
      btn.setAttribute('tabindex', '-1');
    } else {
      btn.addEventListener('click', () => selectEmoji(panel, em));
    }
    frag.appendChild(btn);
  });
  grid.appendChild(frag);
}

// ── Search ────────────────────────────────────────────────────────────────
[1, 2].forEach(panel => {
  PANELS[panel].search.addEventListener('input', () => {
    renderGrid(panel, getCurrentList(panel));
  });
});

// ── View-switch helpers (inline style beats any author CSS display rule) ──
function showResultBox() {
  comboGallery.style.display = 'none';
  resultBox.style.display    = '';     // reverts to CSS flex
}

function showGalleryView() {
  resultBox.style.display    = 'none';
  comboGallery.style.display = '';     // reverts to CSS flex
}

// ── Combo gallery cache ───────────────────────────────────────────────────
const combosCache = {};

async function loadAllCombosFor(emoji) {
  console.log('Loading combos for', emoji);

  if (combosCache[emoji]) {
    showCombosGallery(combosCache[emoji]);
    return;
  }

  // Show gallery immediately with spinner
  showGalleryView();
  galleryLoadingEl.style.display = '';
  comboGalleryGrid.innerHTML = '';

  try {
    const params = new URLSearchParams({ emoji });
    const res = await fetch(`/api/combos-for/?${params}`);
    if (!res.ok) throw new Error(`API ${res.status}`);
    const data = await res.json();
    combosCache[emoji] = data.combos || [];
    console.log('Combos found', combosCache[emoji].length);
    showCombosGallery(combosCache[emoji]);
  } catch (err) {
    console.error('Failed to load combos:', err);
    // Stay in gallery view — show error inside gallery, not in result box
    galleryLoadingEl.style.display = 'none';
    comboGalleryGrid.innerHTML = '<p class="picker__empty">Could not load combos — try again.</p>';
  }
}

function showCombosGallery(combos) {
  showGalleryView();
  galleryLoadingEl.style.display = 'none';
  comboGalleryGrid.innerHTML = '';

  // Build the compatible set so renderGrid can disable non-matching emojis in panel 2
  compatibleEmojisSet = new Set(combos.map(c => c.emoji2));
  // Re-render panel 2 with disabled state applied (keeps current tab / search)
  renderGrid(2, getCurrentList(2));

  if (combos.length === 0) {
    comboGalleryGrid.innerHTML = '<p class="picker__empty">No combos found for this emoji.</p>';
    return;
  }

  const frag = document.createDocumentFragment();
  combos.forEach(({ emoji2, url }) => {
    const card = document.createElement('button');
    card.className = 'gallery-card';
    card.title = `${slot1Emoji} + ${emoji2} — click to select`;
    card.setAttribute('aria-label', `Combo: ${slot1Emoji} + ${emoji2}`);

    const img = document.createElement('img');
    img.src = url;
    img.alt = `${slot1Emoji}+${emoji2}`;
    img.loading = 'lazy';
    img.onerror = () => { card.style.display = 'none'; };

    const label = document.createElement('span');
    label.className = 'gallery-card__label';
    label.textContent = emoji2;

    card.appendChild(img);
    card.appendChild(label);
    card.addEventListener('click', () => selectEmoji(2, emoji2));
    frag.appendChild(card);
  });
  comboGalleryGrid.appendChild(frag);
}

// ── Select emoji ──────────────────────────────────────────────────────────
function setSlotEmoji(panel, emoji) {
  if (panel === 1) slot1Emoji = emoji; else slot2Emoji = emoji;
  const { chip } = PANELS[panel];
  chip.textContent = emoji;
  chip.classList.toggle('cook__chip--filled', !!emoji);
}

function selectEmoji(panel, emoji) {
  addToRecent(emoji);

  if (panel === 1) {
    console.log('FIRST EMOJI SELECTED', emoji);
    setSlotEmoji(1, emoji);

    // Always reset slot2 so we never auto-cook from panel-1 selection
    setSlotEmoji(2, '');
    comboUrl = '';
    btnCopy.disabled = true;
    btnDownload.disabled = true;

    // Clear compat filter so panel 2 shows all enabled while fetch is in-flight
    compatibleEmojisSet = null;
    renderTabs(1);
    renderGrid(1, getCurrentList(1));
    renderTabs(2);
    renderGrid(2, getCurrentList(2)); // all enabled until showCombosGallery fires

    PANELS[1].chip.animate([
      { transform:'scale(1.3)' }, { transform:'scale(.9)' }, { transform:'scale(1)' },
    ], { duration: 280, easing:'ease-out' });

    loadAllCombosFor(emoji);
    return; // never fall through to cookCombo
  }

  // ── Panel 2 ──
  console.log('SECOND EMOJI SELECTED', emoji);
  setSlotEmoji(2, emoji);
  renderTabs(2);
  renderGrid(2, getCurrentList(2));

  PANELS[2].chip.animate([
    { transform:'scale(1.3)' }, { transform:'scale(.9)' }, { transform:'scale(1)' },
  ], { duration: 280, easing:'ease-out' });

  if (slot1Emoji && slot2Emoji) cookCombo();
}

// ── Cook combo ────────────────────────────────────────────────────────────
async function cookCombo() {
  console.log('Cooking single combo', slot1Emoji, slot2Emoji);
  showState('loading'); // also calls showResultBox() → hides gallery
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
      showState('result');
      resultImg.src = validUrl;
      resultImg.style.display = '';
      resultBox.classList.add('has-result');
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
  // Switch to result-box view (inline style wins over any CSS display rule)
  showResultBox();

  // Hide all child states using inline style — CSS display:flex/block on these
  // elements overrides the UA [hidden] attribute, so we must use style.display.
  resultPlaceholder.style.display = 'none';
  resultLoading.style.display     = 'none';
  resultImg.style.display         = 'none';
  resultError.style.display       = 'none';
  resultBox.classList.remove('has-result');

  if (state === 'loading') resultLoading.style.display = '';
  if (state === 'error')   resultError.style.display   = '';
  if (state === 'idle')    resultPlaceholder.style.display = '';
  // 'result': caller sets resultImg.style.display='' and adds has-result class
}

// ── Surprise me ───────────────────────────────────────────────────────────
// Fetches a guaranteed-valid combo from the backend and shows it directly.
// Retries up to MAX_RETRIES times if the image fails to load (e.g. CDN 404).
async function handleSurprise(retriesLeft = 3) {
  showState('loading');
  btnSurprise.disabled = true;

  try {
    const res = await fetch('/api/random-combo/');
    if (!res.ok) throw new Error(`API ${res.status}`);
    const { emoji1, emoji2, url } = await res.json();

    // Verify the image actually loads before committing to this pair
    const validUrl = await findValidImage([url]);
    if (!validUrl) {
      if (retriesLeft > 0) { btnSurprise.disabled = false; return handleSurprise(retriesLeft - 1); }
      throw new Error('Image failed to load after retries');
    }

    // Update both pickers — no compat filter, no gallery
    compatibleEmojisSet = null;
    [[1, emoji1], [2, emoji2]].forEach(([panel, emoji]) => {
      addToRecent(emoji);
      setActiveTab(panel, categoryOf(emoji));
      setSlotEmoji(panel, emoji);
      PANELS[panel].search.value = '';
      renderTabs(panel);
      renderGrid(panel, getCurrentList(panel));

      PANELS[panel].chip.animate([
        {transform:'rotate(-6deg) scale(1.15)'},
        {transform:'rotate(6deg)  scale(1.15)'},
        {transform:'rotate(0)     scale(1)'},
      ], {duration:400, easing:'ease-out'});
    });

    // Show result directly — no extra API round-trip needed
    comboUrl = validUrl;
    showState('result');
    resultImg.src = validUrl;
    resultImg.style.display = '';
    resultBox.classList.add('has-result');
    btnCopy.disabled = false;
    btnDownload.disabled = false;

    // Save to My Combos
    const isNew = !getCombos().some(c =>
      (c.emoji1 === emoji1 && c.emoji2 === emoji2) ||
      (c.emoji1 === emoji2 && c.emoji2 === emoji1)
    );
    saveCombo(emoji1, emoji2, validUrl);
    if (isNew) window.showToast('Saved to My Combos!', '⭐');

  } catch (err) {
    console.error('Surprise failed:', err);
    showState('error');
    window.showToast('Could not load a combo — try again!', '⚠️', true);
  } finally {
    btnSurprise.disabled = false;
  }
}

btnSurprise.addEventListener('click', () => handleSurprise());

// ── Reset ─────────────────────────────────────────────────────────────────
btnReset.addEventListener('click', () => {
  compatibleEmojisSet = null; // restore all panel-2 emojis to enabled
  [1, 2].forEach(panel => {
    setSlotEmoji(panel, '');
    renderGrid(panel, getCurrentList(panel));
  });
  comboUrl = '';
  resultImg.src = '';
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

// ── Copy mashup image ────────────────────────────────────────────────────
btnCopy.addEventListener('click', async () => {
  if (!comboUrl) return;

  if (navigator.clipboard?.write && window.ClipboardItem) {
    try {
      await navigator.clipboard.write([
        new ClipboardItem({
          'image/png': fetch(`/api/proxy/?url=${encodeURIComponent(comboUrl)}`).then(res => {
            if (!res.ok) throw new Error('Image fetch failed');
            return res.blob();
          }),
        }),
      ]);
      window.showToast('Mashup copied — paste it anywhere!', '✅');
      return;
    } catch (err) {
      console.error('Image copy failed, falling back to text:', err);
    }
  }

  // Fallback for browsers without image-clipboard support
  const text = slot1Emoji + slot2Emoji;
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text)
      .then(() => window.showToast(`Image copy isn't supported here — copied ${text} instead`, '⚠️', true))
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
[1, 2].forEach(panel => {
  renderTabs(panel);
  renderGrid(panel, getCurrentList(panel));
});
showState('idle');
renderCombos(); // restore saved combos from localStorage
