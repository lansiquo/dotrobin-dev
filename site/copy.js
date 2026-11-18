// Project cards: shows the copy buttons and copies their command. Without JavaScript, or without the clipboard API,
// the buttons stay hidden and the command text stays on the page. A button copies its data-copy text, or the text of
// the element named by data-copy-from, so a version filled in at deploy is copied as shown.
(() => {
  'use strict';
  const buttons = document.querySelectorAll('button.copy[hidden]');
  if (!buttons.length || !navigator.clipboard || !window.isSecureContext) return;

  const status = document.createElement('p');
  status.className = 'visually-hidden';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  document.body.append(status);

  for (const button of buttons) {
    const source = button.dataset.copyFrom ? document.getElementById(button.dataset.copyFrom) : null;
    const text = () => (source ? source.textContent : button.dataset.copy || '').trim();
    if (!text()) continue;
    const label = button.textContent;
    let timer = 0;
    button.addEventListener('click', () => {
      navigator.clipboard.writeText(text()).then(() => {
        button.textContent = 'copied ✓';
        status.textContent = '';
        // A fresh text node after clearing makes screen readers announce it again on a second copy.
        setTimeout(() => { status.textContent = 'copied'; }, 50);
        clearTimeout(timer);
        timer = setTimeout(() => { button.textContent = label; status.textContent = ''; }, 1500);
      }, () => {
        status.textContent = 'copy failed';
      });
    });
    button.hidden = false;
  }
})();
