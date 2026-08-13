/* OSINT 100X — Main JS */
'use strict';

// ── SIDEBAR TOGGLE ────────────────────────────────────────
const sidebar = document.querySelector('.sidebar');
const toggle  = document.querySelector('.mobile-toggle');

if (toggle && sidebar) {
  toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.addEventListener('click', e => {
    if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
}

// ── SOURCE ACCORDION ─────────────────────────────────────
document.querySelectorAll('.source-header').forEach(header => {
  header.addEventListener('click', () => {
    const block = header.closest('.source-block');
    const records = block.querySelector('.source-records');
    const icon = header.querySelector('.accordion-icon');
    records.classList.toggle('hidden');
    if (icon) icon.textContent = records.classList.contains('hidden') ? '▶' : '▼';
  });
});

// ── SEARCH SPINNER ────────────────────────────────────────
const searchForm = document.querySelector('.search-form');
const searchBtn  = document.querySelector('#search-btn');

if (searchForm && searchBtn) {
  searchForm.addEventListener('submit', () => {
    searchBtn.disabled = true;
    searchBtn.innerHTML = '<span class="spinner"></span> Searching...';
  });
}

// ── TIER CARD SELECT ─────────────────────────────────────
document.querySelectorAll('.tier-card').forEach(card => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.tier-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    const tier = card.dataset.tier;
    const input = document.querySelector('#selected-tier');
    if (input) input.value = tier;
    const amtEl = document.querySelector('#display-amount');
    if (amtEl) amtEl.textContent = '₹' + card.dataset.price;
  });
});

// ── ALERT DISMISS ────────────────────────────────────────
document.querySelectorAll('.alert-dismiss').forEach(btn => {
  btn.addEventListener('click', () => btn.closest('.alert').remove());
});

// ── COPY TO CLIPBOARD ────────────────────────────────────
document.querySelectorAll('[data-copy]').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = btn.dataset.copy;
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.textContent;
      btn.textContent = '✓ Copied';
      setTimeout(() => (btn.textContent = orig), 1500);
    });
  });
});

// ── SHARE LINK ───────────────────────────────────────────
const shareBtn = document.querySelector('#share-btn');
if (shareBtn) {
  shareBtn.addEventListener('click', async () => {
    const form = document.querySelector('#share-form');
    if (!form) return;
    const fd = new FormData(form);
    const resp = await fetch(form.action, { method: 'POST', body: fd });
    const data = await resp.json();
    if (data.link) {
      navigator.clipboard.writeText(data.link);
      shareBtn.textContent = '✓ Link Copied';
      setTimeout(() => (shareBtn.textContent = '🔗 Share'), 2000);
    }
  });
}

// ── ADMIN QUICK TIER ─────────────────────────────────────
document.querySelectorAll('.quick-tier-select').forEach(sel => {
  sel.addEventListener('change', () => {
    sel.closest('form').submit();
  });
});

// ── AUTO CLOSE ALERTS ────────────────────────────────────
setTimeout(() => {
  document.querySelectorAll('.alert:not(.alert-persist)').forEach(a => {
    a.style.transition = 'opacity .4s';
    a.style.opacity = '0';
    setTimeout(() => a.remove(), 400);
  });
}, 4500);
