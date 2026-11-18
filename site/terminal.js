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
  const span = (cls, text) => el('span', cls ? { class: cls } : {}, text);
  const link = (href, text, external, cls) => {
    const node = el('a', external ? { href, target: '_blank', rel: 'noopener' } : { href }, text);
    if (cls) node.className = cls;
    return node;
  };
  const list = items => items.flatMap((item, i) => (i ? [span('d', ' · '), item] : [item]));

  // The terminal's own files, as its ls and cat show them. Folders hold links; permissions are decoration only.
  const about = document.getElementById('about-txt');
  const ABOUT = about ? about.cloneNode(true) : null;  // kept before clear can remove the original
  if (ABOUT) ABOUT.removeAttribute('id');
  const FILES = {
    'about.txt': { kind: 'file', item: () => span('', 'about.txt') },
    'projects/': { kind: 'dir', item: () => link('#projects', 'projects/'),
      entries: () => [['dir', link('sca-triage.html', 'sca-triage/')], ['dir', link('sast-triage.html', 'sast-triage/')],
        ['dir', link('factory.html', 'software-factory/')]] },
    'writeups/': { kind: 'dir', item: () => link('#writeups', 'writeups/'),
      entries: () => ['blackpearl', 'academy', 'dev', 'blue', 'butler'].map(name => ['file', link(`${name}.html`, `${name}.md`, false, 'y')]) },
  };
  const MODE = { dir: 'drwxr-xr-x', file: '-rw-r--r--' };
  // Own keys only, and "projects", "./projects" or "projects/" all name the same folder.
  const find = path => {
    const name = path.replace(/^(\.\/)+/, '');
    for (const key of [name, `${name}/`]) if (Object.hasOwn(FILES, key)) return key;
    return null;
  };
  const error = text => [span('d', text)];
  const listing = (rows, long) => (long
    ? [el('ul', { class: 'ls-long' }, ...rows.map(([kind, item]) => el('li', {}, span('d', MODE[kind]), ' ', item)))]
    : [el('ul', { class: 'ls-files' }, ...rows.map(([, item]) => el('li', {}, item)))]);

  function ls(args) {
    let long = false;
    const paths = [];
    for (const arg of args) {
      if (arg.startsWith('-') && arg.length > 1) {
        const bad = [...arg.slice(1)].find(flag => flag !== 'l' && flag !== 'a');
        if (bad) return error(`ls: invalid option -- '${bad}'`);
        long = true;  // -l, -a, -la and -al all show the long form
      } else paths.push(arg);
    }
    if (paths.length > 1) return error('ls: one folder at a time');
    if (!paths.length || paths[0] === '.' || paths[0] === './' || paths[0] === '~') {
      return listing(Object.keys(FILES).map(key => [FILES[key].kind, FILES[key].item()]), long);
    }
    const key = find(paths[0]);
    if (!key) return error(`ls: cannot access '${paths[0]}': No such file or directory`);
    const entry = FILES[key];
    return listing(entry.kind === 'dir' ? entry.entries() : [[entry.kind, entry.item()]], long);
  }

  function cat(args) {
    if (!args.length) return error('cat: missing file operand');
    const key = args.length === 1 ? find(args[0]) : null;
    if (key === 'about.txt' && ABOUT) return [...ABOUT.cloneNode(true).childNodes];
    if (key) return error(`cat: ${args[0]}: Is a directory`);
    return error(`cat: ${args.join(' ')}: No such file or directory`);
  }

  const NAMES = ['help', 'ls', 'cat', 'projects', 'writeups', 'resume', 'contact', 'whoami', 'clear'];
  const COMMANDS = {
    help: () => ['commands: ', ...list(NAMES.map(name => span('g', name)))],
    ls,
    cat,
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
    const line = typed.trim();
    const [first, ...args] = line.split(/\s+/);
    const name = first.toLowerCase();
    if (name === 'clear') {
      for (const node of [...out.children]) if (node !== prompt && node !== log) node.remove();
      log.replaceChildren();
      return;
    }
    const echo = el('p', { class: 'cmd' }, el('span', { class: 'ps', 'aria-hidden': 'true' }, '$'), ' ');
    echo.append(line);  // a text node: the typed text is never read as HTML
    log.append(echo);
    if (!name) return;
    // Own keys only: a typed word such as constructor or __proto__ must not reach Object.prototype.
    const answer = Object.hasOwn(COMMANDS, name) ? COMMANDS[name] : null;
    const reply = answer ? answer(args) : [span('d', 'command not found: '), line, span('d', ' · try help')];
    // A listing is a list of its own; everything else is one line.
    log.append(reply.length === 1 && reply[0] instanceof HTMLUListElement ? reply[0] : el('p', {}, ...reply));
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
