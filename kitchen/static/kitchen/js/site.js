/* ════════════════════════════════════════════════════════════════════
   Emoji Kitchen — site.js
   Shared across all pages: toast, nav, scroll animations, FAQ accordion
════════════════════════════════════════════════════════════════════ */
'use strict';

// ── Toast ─────────────────────────────────────────────────────────────────
const toastEl  = document.getElementById('toast');
const toastMsg = document.getElementById('toast-msg');
const toastIco = document.getElementById('toast-icon');
let toastTimer;

window.showToast = function showToast(msg, icon = '✅', isError = false) {
  clearTimeout(toastTimer);
  toastMsg.textContent = msg;
  toastIco.textContent = icon;
  toastEl.classList.toggle('toast--error', isError);
  toastEl.classList.add('show');
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), 2800);
};

// ── FAQ: one open at a time ────────────────────────────────────────────────
document.querySelectorAll('.faq-item').forEach(details => {
  details.addEventListener('toggle', () => {
    if (details.open) {
      document.querySelectorAll('.faq-item').forEach(d => {
        if (d !== details) d.removeAttribute('open');
      });
    }
  });
});

// ── Mobile nav hamburger ──────────────────────────────────────────────────
const hamburger = document.getElementById('nav-hamburger');
const drawer    = document.getElementById('nav-drawer');

hamburger?.addEventListener('click', () => {
  const isOpen = hamburger.classList.toggle('open');
  drawer.classList.toggle('open', isOpen);
  hamburger.setAttribute('aria-expanded', isOpen);
  drawer.setAttribute('aria-hidden', !isOpen);
});

// Close drawer on link click
document.querySelectorAll('[data-close-drawer]').forEach(link => {
  link.addEventListener('click', () => {
    hamburger.classList.remove('open');
    drawer.classList.remove('open');
    hamburger.setAttribute('aria-expanded', 'false');
    drawer.setAttribute('aria-hidden', 'true');
  });
});

// ── "Others" dropdown ─────────────────────────────────────────────────────
// Opens on hover with the mouse (pure CSS), and on click / Enter / Space for touch screens and keyboards.
const othersItem = document.querySelector('.nav__item--others');
const othersBtn  = document.getElementById('nav-others-btn');

function setOthersOpen(open) {
  if (!othersItem || !othersBtn) return;
  othersItem.classList.toggle('is-open', open);
  othersBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
}

if (othersItem && othersBtn) {
  othersBtn.addEventListener('click', () => setOthersOpen(!othersItem.classList.contains('is-open')));
  othersItem.addEventListener('mouseenter', () => othersBtn.setAttribute('aria-expanded', 'true'));
  othersItem.addEventListener('mouseleave', () => {
    if (!othersItem.classList.contains('is-open')) othersBtn.setAttribute('aria-expanded', 'false');
  });
  document.addEventListener('click', e => {
    if (!othersItem.contains(e.target)) setOthersOpen(false);
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && othersItem.classList.contains('is-open')) {
      setOthersOpen(false);
      othersBtn.focus();
    }
  });
}

// ── Sticky nav shadow ─────────────────────────────────────────────────────
const siteHeader = document.getElementById('site-header');
window.addEventListener('scroll', () => {
  siteHeader.classList.toggle('scrolled', window.scrollY > 8);
}, { passive: true });

// ── Scroll-in animations (Intersection Observer) ──────────────────────────
const animObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      animObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0 });

document.querySelectorAll('.animate-up').forEach(el => animObserver.observe(el));
