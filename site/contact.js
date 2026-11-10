// "Contact" and the Email links open a panel instead of jumping to the footer or a mail app.
// Without JavaScript the links still go to the footer links or open the mail app.
(() => {
  'use strict';
  // Collected before the panel is built, so its own "Write an email" link stays a plain mailto.
  const triggers = [...document.querySelectorAll('a[href="#contact"], a[href^="mailto:"]')];
  const footer = document.getElementById('contact');
  if (!triggers.length || !footer || typeof HTMLDialogElement !== 'function') return;

  const email = 'lansiquo@gmail.com';
  const linkedin = footer.querySelector('a[href*="linkedin.com"]');
  const resume = footer.querySelector('a[href$=".pdf"]');
  const subject = 'Application security role: ';

  const el = (tag, attrs = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    node.append(...children);
    return node;
  };

  const status = el('output', { class: 'contact-copied', 'aria-live': 'polite' });
  const copy = el('button', { type: 'button', class: 'contact-copy' }, 'Copy');
  const rows = [
    el('div', { class: 'contact-email' },
      el('span', { class: 'contact-address' }, email), copy),
    el('a', { class: 'contact-action', href: `mailto:${email}?subject=${encodeURIComponent(subject)}` },
      'Write an email', el('span', { 'aria-hidden': 'true' }, '→')),
  ];
  if (linkedin) rows.push(el('a', { class: 'contact-action', href: linkedin.href, target: '_blank', rel: 'noopener' },
    'Message me on LinkedIn', el('span', { 'aria-hidden': 'true' }, '↗')));
  if (resume) rows.push(el('a', { class: 'contact-action', href: resume.href, target: '_blank', rel: 'noopener' },
    'Download my résumé (PDF)', el('span', { 'aria-hidden': 'true' }, '↓')));

  const close = el('button', { type: 'button', class: 'contact-close', 'aria-label': 'Close' }, '×');
  const dialog = el('dialog', { class: 'contact-dialog', 'aria-labelledby': 'contact-title' },
    el('div', { class: 'contact-head' },
      el('h2', { id: 'contact-title' }, 'Get in touch'), close),
    el('p', { class: 'contact-open' }, el('span', { class: 'contact-dot', 'aria-hidden': 'true' }),
      'Open to application security and product security roles, Toronto.'),
    el('p', { class: 'contact-why' },
      'Hiring, or want a walkthrough of sast-triage, sca-triage or one of the lab writeups? Email is the fastest way to reach me.'),
    ...rows, status);
  document.body.append(dialog);

  let opener = null;
  function open(event) {
    event.preventDefault();
    opener = event.currentTarget;
    status.textContent = '';
    dialog.showModal();
    copy.focus();
  }
  for (const a of triggers) {
    a.setAttribute('aria-haspopup', 'dialog');
    a.addEventListener('click', open);
  }
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => { if (opener) opener.focus(); });

  copy.addEventListener('click', async () => {
    let ok = false;
    try { await navigator.clipboard.writeText(email); ok = true; } catch {
      const range = document.createRange();
      range.selectNodeContents(dialog.querySelector('.contact-address'));
      const sel = getSelection(); sel.removeAllRanges(); sel.addRange(range);
      try { ok = document.execCommand('copy'); } catch { ok = false; }
    }
    copy.textContent = ok ? 'Copied' : 'Copy';
    status.textContent = ok ? `${email} copied to your clipboard.` : 'Select the address above and copy it.';
    setTimeout(() => { copy.textContent = 'Copy'; }, 2000);
  });
})();
