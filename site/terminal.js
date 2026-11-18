// Homepage terminal: adds a prompt you can type a few commands into. Without JavaScript the window shows the same
// text and links, ending in a still prompt. Every answer is built with DOM methods and textContent: what you type
// is only ever shown as text, never parsed as HTML.
(() => {
  'use strict';
  const term = document.querySelector('.term');
  const out = term && term.querySelector('.term-out');
  const prompt = out && out.querySelector('.term-prompt');
  if (!prompt) return;

  const RESUME = 'Robin_Lansiquot_Resume.pdf';
  const el = (tag, attrs = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    node.append(...children);
    return node;
  };
  const span = (cls, text) => el('span', { class: cls }, text);
  const link = (href, text, external) => el('a', external ? { href, target: '_blank', rel: 'noopener' } : { href }, text);
  const list = items => items.flatMap((item, i) => (i ? [span('d', ' · '), item] : [item]));

  const NAMES = ['help', 'projects', 'writeups', 'resume', 'contact', 'whoami', 'clear'];
  const COMMANDS = {
    help: () => ['commands: ', ...list(NAMES.map(name => span('g', name)))],
    projects: () => list([link('sca-triage.html', 'sca-triage'), link('sast-triage.html', 'sast-triage'), link('factory.html', 'software-factory')]),
    writeups: () => list(['blackpearl', 'academy', 'dev', 'blue', 'butler'].map(name => link(`${name}.html`, name))),
    resume: () => ['opening ', link(RESUME, RESUME, true)],
    contact: () => list([link('mailto:lansiquo@gmail.com', 'email'), link('https://www.linkedin.com/in/robin-lansiquot/', 'linkedin', true),
      link('https://github.com/lansiquo', 'github', true)]),
    whoami: () => ['Robin Lansiquot · ', span('b', 'application security engineer')],
    sudo: () => [span('r', 'nice try.'), ' this incident will be reported.'],
  };

  const input = el('input', { id: 'term-in', type: 'text', maxlength: '80', autocomplete: 'off', autocapitalize: 'off', spellcheck: 'false', enterkeyhint: 'send' });
  const label = el('label', { for: 'term-in', class: 'visually-hidden' }, 'Type a command, then press Enter. Try help.');
  const log = el('div', { class: 'term-log', 'aria-live': 'polite' });
  prompt.before(log);
  prompt.append(label, input);
  const hint = document.querySelector('.hint');
  if (hint) hint.hidden = false;

  function run(typed) {
    const words = typed.trim().split(/\s+/);
    const name = words[0].toLowerCase();
    if (name === 'clear') {
      for (const node of [...out.children]) if (node !== prompt && node !== log) node.remove();
      log.replaceChildren();
      return;
    }
    const echo = el('p', { class: 'cmd' }, el('span', { class: 'ps', 'aria-hidden': 'true' }, '$'), ' ');
    echo.append(typed);  // a text node: the typed text is never read as HTML
    log.append(echo);
    if (!name) return;
    const answer = COMMANDS[name];
    log.append(el('p', {}, ...(answer ? answer() : [span('d', 'command not found: '), typed.trim(), span('d', ' · try help')])));
    if (name === 'resume') window.open(RESUME, '_blank', 'noopener');
  }

  input.addEventListener('keydown', event => {
    if (event.key !== 'Enter' || event.isComposing) return;
    event.preventDefault();
    run(input.value);
    input.value = '';
    prompt.classList.remove('typed');
    input.scrollIntoView({ block: 'nearest' });
  });
  input.addEventListener('input', () => prompt.classList.toggle('typed', input.value !== ''));
  // A click on the window, other than on a link or a text selection, puts the cursor in the prompt.
  term.addEventListener('click', event => {
    if (event.target.closest('a') || String(getSelection())) return;
    input.focus({ preventScroll: true });
  });
})();
