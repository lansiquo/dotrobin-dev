// Homepage terminal: turns the static transcript into a small macOS zsh session over a virtual home folder.
// Without JavaScript the window shows the same facts and links, ending in a still prompt. Every line is built with
// DOM methods and text nodes: what you type is only ever shown as text, and links come only from the constant tree
// below, never from typed input. Commands and paths are looked up among own keys only.
(() => {
  'use strict';
  const term = document.querySelector('.term');
  const out = term && term.querySelector('.term-out');
  const prompt = out && out.querySelector('.term-prompt');
  if (!prompt) return;

  // ---- small DOM helpers ----
  const SAFE_HREF = /^(#[a-z-]+|[a-z-]+\.html|Robin_Lansiquot_Resume\.pdf|mailto:lansiquo@gmail\.com|https:\/\/(www\.linkedin\.com|github\.com|www\.npmjs\.com)\/[A-Za-z0-9/._-]*)$/;
  const el = (tag, cls, ...children) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    node.append(...children);
    return node;
  };
  const span = (cls, text) => el('span', cls, text);
  const link = (href, text, cls) => {
    if (!SAFE_HREF.test(href)) return span(cls, text);
    const node = el('a', cls, text);
    node.href = href;
    if (/^https:|\.pdf$/.test(href)) { node.target = '_blank'; node.rel = 'noopener'; }
    return node;
  };

  // ---- versions: read from the page's own data-release labels, which the deploy fills. Read once, before `clear`
  // can remove the transcript's labels. ----
  const version = tool => {
    const label = document.querySelector(`[data-release="${tool}"][data-release-format="X.Y.Z"]`);
    const text = label ? label.textContent.trim() : '';
    return /^[0-9]+\.[0-9]+\.[0-9]+$/.test(text) ? text : '';
  };
  const SCA = version('sca-triage');
  const SAST = version('sast-triage');
  const v = (text, ver) => (ver ? `${text}${ver}` : '');

  // ---- the virtual home folder: every word in a file comes from this site, its case studies or the resume ----
  const lines = (...rows) => rows.filter(row => row !== null).join('\n');
  const file = (body, href, links = []) => ({ body, href, links });
  const dir = (entries, href) => ({ dir: true, entries, href });
  const HOME = dir({
    '.zshrc': file(lines('# Find what matters. Fix it safely.', "PROMPT='%n@%m %~ %% '")),
    'about.txt': file(lines('Most findings don’t matter. The reachable ones do. I co-led a CI/CD security pipeline for over 60,000 applications in financial services, and now build open-source tools that find what matters and fix it safely.')),
    'contact.vcf': file(lines('BEGIN:VCARD', 'VERSION:3.0', 'FN:Robin Lansiquot', 'TITLE:Application Security Engineer',
      'ADR:;;;Toronto;;;Canada', 'EMAIL:lansiquo@gmail.com', 'URL:https://dotrobin.dev',
      'URL:https://www.linkedin.com/in/robin-lansiquot/', 'URL:https://github.com/lansiquo', 'END:VCARD'), '#contact',
    [['mailto:lansiquo@gmail.com', 'email'], ['https://www.linkedin.com/in/robin-lansiquot/', 'LinkedIn'], ['https://github.com/lansiquo', 'GitHub']]),
    projects: dir({
      'sca-triage': dir({
        'README.md': file(lines('# sca-triage',
          'Ranks npm vulnerabilities by whether your code loads the vulnerable package, applies the smallest safe upgrades and checks them with the project’s tests.', '',
          'OWASP NodeGoat: 1,479 packages scanned, 12 of 180 vulnerable packages to fix now.',
          v('Version ', SCA) ? `${v('Version ', SCA)} · npm · MIT` : 'npm · MIT',
          '$ npx sca-triage'), 'sca-triage.html',
        [['sca-triage.html', 'case study'], ['https://www.npmjs.com/package/sca-triage', 'npm']]),
      }, 'sca-triage.html'),
      'sast-triage': dir({
        'README.md': file(lines('# sast-triage',
          'Labels each Semgrep finding new or pre-existing, ranks it P1–P3 and fails only on new P1 findings or incomplete scans.', '',
          'OWASP NodeGoat: 7 real P1s in a full scan; the last two pull requests added none, so neither was blocked.',
          v('Version ', SAST) ? `${v('Version ', SAST)} · GitHub Action · MIT` : 'GitHub Action · MIT',
          SAST ? `- uses: lansiquo/sast-triage@v${SAST}` : null), 'sast-triage.html',
        [['sast-triage.html', 'case study'], ['https://github.com/lansiquo/sast-triage', 'GitHub']]),
      }, 'sast-triage.html'),
      'software-factory': dir({
        'README.md': file(lines('# Software factory: how these tools ship',
          'A coordinator picks up the next item on a roadmap I approved. One agent writes the change, a different one tries to break it, and nothing merges until it passes. Product and security decisions stay with me.', '',
          '1 in 3 QA runs sent a change back before it could merge.',
          'sast-triage scans every pull request to this website and both tools.'), 'factory.html',
        [['factory.html', 'how it works']]),
      }, 'factory.html'),
    }, '#projects'),
    'resume.pdf': Object.assign(file(null, 'Robin_Lansiquot_Resume.pdf'), { size: 91753 }),
    writeups: dir(Object.fromEntries([
      ['blackpearl', 'Blackpearl', 'Linux', 'Outdated web CMS → misconfigured SUID binary'],
      ['academy', 'Academy', 'Linux', 'Exposed credentials → unrestricted file upload → root-run backup script'],
      ['dev', 'Dev', 'Linux', 'Open NFS share → overly permissive sudo rule'],
      ['blue', 'Blue', 'Windows', 'Unpatched SMBv1 on Windows 7, checked against MS17-010'],
      ['butler', 'Butler', 'Windows', 'Exposed Jenkins server → unquoted service path'],
    ].map(([name, title, os, chain]) => [`${name}.md`,
      file(lines(`# ${title}`, `${os} · ${chain}`), `${name}.html`, [[`${name}.html`, 'read the writeup']])])), '#writeups'),
  });

  // ---- paths ----
  const own = (obj, key) => Object.hasOwn(obj, key);
  let cwd = [];          // [] is ~
  let oldpwd = null;
  const show = parts => (parts.length ? `~/${parts.join('/')}` : '~');
  // Returns { node, parts } for a typed path, or null. Only ~ (and /Users/robin) count as absolute.
  const resolve = arg => {
    let parts;
    if (arg === '~' || arg.startsWith('~/')) parts = arg.slice(1).split('/');
    else if (arg === '/Users/robin' || arg.startsWith('/Users/robin/')) parts = arg.slice(12).split('/');
    else if (arg.startsWith('/')) return null;
    else parts = [...cwd, ...arg.split('/')];
    const stack = [];
    for (const part of parts) {
      if (!part || part === '.') continue;
      if (part === '..') stack.pop(); else stack.push(part);
    }
    let node = HOME;
    for (const part of stack) {
      if (!node.dir || !own(node.entries, part)) return null;
      node = node.entries[part];
    }
    if (arg.endsWith('/') && !node.dir) return null;
    return { node, parts: stack };
  };
  const bytes = text => new TextEncoder().encode(text).length;
  const size = node => (node.dir ? 64 + 32 * Object.keys(node.entries).length : node.size || bytes(node.body || ''));
  const links = node => (node.dir ? 2 + Object.values(node.entries).filter(n => n.dir).length : 1);
  const visible = (node, all) => Object.keys(node.entries).sort().filter(name => all || !name.startsWith('.'));
  const nameOf = (name, node, withLink = true) => {
    const cls = node.dir ? 'b' : /\.(pdf|vcf)$/.test(name) ? 'y' : '';
    const label = node.dir ? `${name}/` : name;
    return withLink && node.href && name !== '.' && name !== '..' ? link(node.href, label, cls) : span(cls, label);
  };

  // ---- output ----
  const log = el('div', 'term-log');
  log.setAttribute('aria-live', 'polite');
  const res = (...children) => el('div', 'res', ...children);
  const text = (cls, value) => res(span(cls, value));
  const err = value => text('', value);
  const joinNodes = (nodes, sep) => nodes.flatMap((node, i) => (i ? [typeof sep === 'string' ? sep : sep.cloneNode(true), node] : [node]));
  const linkRow = pairs => res(span('d', '→ '), ...joinNodes(pairs.map(([href, label]) => link(href, label, 'b')), span('d', ' · ')));

  // ---- commands ----
  const DATE = 'Nov 18 10:42';
  function ls(args) {
    let long = false, all = false;
    const paths = [];
    for (const arg of args) {
      if (arg.startsWith('-') && arg.length > 1) {
        for (const flag of arg.slice(1)) {
          if (flag === 'l') long = true;
          else if (flag === 'a') all = true;
          else return [err(`ls: invalid option -- '${flag}'`), err('usage: ls [-la] [file ...]')];
        }
      } else paths.push(arg);
    }
    if (!paths.length) paths.push('.');
    const blocks = [], missing = [];
    for (const path of paths) {
      const found = resolve(path);
      if (!found) missing.push(err(`ls: ${path}: No such file or directory`));
      else blocks.push([path, found.node]);
    }
    const row = (name, node) => {
      if (!long) return nameOf(name, node);
      return el('span', '', span('d', `${node.dir ? 'drwxr-xr-x' : '-rw-r--r--'}  ${String(links(node)).padStart(2)} robin  staff  `),
        String(size(node)).padStart(5), span('d', ` ${DATE} `), nameOf(name, node));
    };
    const listing = (entries) => {
      if (long) {
        const total = entries.reduce((sum, [, node]) => sum + Math.max(8, Math.ceil(size(node) / 4096) * 8), 0);
        return [text('d', `total ${total}`), ...entries.map(([name, node]) => res(row(name, node)))];
      }
      return [res(...joinNodes(entries.map(([name, node]) => row(name, node)), '  '))];
    };
    const output = [...missing];
    const files = blocks.filter(([, node]) => !node.dir);
    const dirs = blocks.filter(([, node]) => node.dir);
    if (files.length) output.push(...listing(files));
    dirs.forEach(([path, node], i) => {
      if (blocks.length > 1) output.push(text('', `${files.length || i ? '\n' : ''}${path}:`));
      const parent = resolve(`${path}/..`);
      const entries = visible(node, all).map(name => [name, node.entries[name]]);
      if (all) entries.unshift(['.', node], ['..', parent ? parent.node : node]);
      output.push(...listing(entries));
    });
    return output;
  }

  function cd([arg]) {
    let target = arg;
    if (arg === undefined || arg === '~') target = '~';
    else if (arg === '-') {
      if (oldpwd === null) return [err('cd: OLDPWD not set')];
      target = `~/${oldpwd.join('/')}`;
    }
    const found = resolve(target);
    if (!found) return [err(`cd: no such file or directory: ${arg}`)];
    if (!found.node.dir) return [err(`cd: not a directory: ${arg}`)];
    oldpwd = cwd;
    cwd = found.parts;
    return arg === '-' ? [text('', show(cwd))] : [];
  }

  function cat(args) {
    if (!args.length) return [text('d', 'cat: reads a file. Try cat about.txt')];
    return args.flatMap(arg => {
      const found = resolve(arg);
      if (!found) return [err(`cat: ${arg}: No such file or directory`)];
      const node = found.node;
      if (node.dir) return [err(`cat: ${arg}: Is a directory`)];
      if (node.body === null) return [res(span('d', `${arg} is a PDF. Try `), span('g', `open ${arg}`))];
      return [text('', node.body), ...(node.links.length ? [linkRow(node.links)] : [])];
    });
  }

  let leaving = 0;
  function open([arg]) {
    if (!arg) return [err('usage: open <file or folder>')];
    const found = resolve(arg);
    if (!found) return [err(`The file /Users/robin/${[...cwd, arg].join('/').replace(/^\/+/, '')} does not exist.`)];
    let node = found.node;
    if (node.dir && own(node.entries, 'README.md')) node = node.entries['README.md'];
    if (!node.href || !SAFE_HREF.test(node.href)) return [res(span('d', `nothing to open for ${arg}. Try `), span('g', `cat ${arg}`))];
    const href = node.href;
    if (href.endsWith('.pdf')) window.open(href, '_blank', 'noopener');
    else {
      clearTimeout(leaving);
      leaving = setTimeout(() => { location.assign(href); }, 400);
    }
    return [res(span('d', 'opening '), link(href, arg, 'b'))];
  }

  function tree([arg]) {
    const found = resolve(arg || '.');
    if (!found) return [err(`${arg} [error opening dir]`), text('', '\n0 directories, 0 files')];
    if (!found.node.dir) return [text('', arg), text('', '\n0 directories, 1 file')];
    let dirs = 0, files = 0;
    const rows = [text('b', arg || '.')];
    const walk = (node, pre) => visible(node, false).forEach((name, i, names) => {
      const child = node.entries[name], last = i === names.length - 1;
      rows.push(res(span('d', `${pre}${last ? '└── ' : '├── '}`), child.href ? link(child.href, name, child.dir ? 'b' : '') : span(child.dir ? 'b' : '', name)));
      if (child.dir) { dirs += 1; walk(child, pre + (last ? '    ' : '│   ')); } else files += 1;
    });
    walk(found.node, '');
    rows.push(text('', `\n${dirs} director${dirs === 1 ? 'y' : 'ies'}, ${files} file${files === 1 ? '' : 's'}`));
    return rows;
  }

  const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const two = n => String(n).padStart(2, '0');
  const stamp = d => `${DAYS[d.getDay()]} ${MONTHS[d.getMonth()]} ${String(d.getDate()).padStart(2)} ${two(d.getHours())}:${two(d.getMinutes())}:${two(d.getSeconds())}`;
  const zone = d => {
    try {
      const part = new Intl.DateTimeFormat('en-US', { timeZoneName: 'short' }).formatToParts(d).find(p => p.type === 'timeZoneName');
      return part ? part.value : '';
    } catch { return ''; }
  };
  let tty = 0;
  const lastLogin = () => el('p', 'd login', `Last login: ${stamp(new Date())} on ttys${String(tty++).padStart(3, '0')}`);

  const ENV = { USER: 'robin', HOME: '/Users/robin', SHELL: '/bin/zsh', HOST: 'dotrobin.local', LOGNAME: 'robin' };
  const expand = word => word.replace(/\$([A-Z]+)/g, (_, name) => (name === 'PWD' ? `/Users/robin${cwd.length ? `/${cwd.join('/')}` : ''}` : own(ENV, name) ? ENV[name] : ''));

  const MAN = {
    cat: ['concatenate and print files', 'cat [file ...]'], cd: ['change the working directory', 'cd [dir | .. | ~ | -]'],
    clear: ['clear the terminal screen (also Ctrl+L or Cmd+K)', 'clear'], date: ['display the date and time', 'date'],
    echo: ['write arguments to the standard output', 'echo [string ...]'], exit: ['log out of the shell', 'exit'],
    help: ['list the commands this terminal knows', 'help'], history: ['list the commands you typed', 'history'],
    hostname: ['print the name of this host', 'hostname'], id: ['return user identity', 'id'],
    ls: ['list directory contents', 'ls [-la] [file ...]'], man: ['format and display manual pages', 'man command'],
    neofetch: ['show who runs this site', 'neofetch'], open: ['open a file or folder: a project opens its case study', 'open file ...'],
    pwd: ['return working directory name', 'pwd'], tree: ['list contents of directories in a tree-like format', 'tree [dir]'],
    uname: ['display information about the system', 'uname [-a]'], whoami: ['display effective user id', 'whoami'],
  };

  const ART = [
    ['b', "      .:'"], ['b', "  __ :'__"], ['b', ".'`  `-'  ``."], ['y', ":          .-'"],
    ['y', ":         :"], ['r', " :         `-;"], ['r', "  `.__.-.__.'"],
  ];
  function neofetch() {
    const tools = [SCA ? `sca-triage v${SCA}` : 'sca-triage', SAST ? `sast-triage v${SAST}` : 'sast-triage'].join(' · ');
    const info = [
      [['g', 'robin'], ['', '@'], ['g', 'dotrobin']], [['', '--------------']],
      [['b', 'Role'], ['', ': application security engineer']],
      [['b', 'Focus'], ['', ': SCA · SAST · vulnerability management']],
      [['b', 'Scale'], ['', ': co-led a CI/CD security pipeline for 60,000+ applications']],
      [['b', 'Tools'], ['', `: ${tools}`]],
      [['b', 'Certs'], ['', ': eJPT certified · PNPT in progress']],
      [['b', 'Location'], ['', ': Toronto, Canada']],
    ];
    const art = el('div', 'neo-art', ...ART.map(([cls, row]) => el('div', cls, row)));
    art.setAttribute('aria-hidden', 'true');
    const facts = el('div', 'neo-info', ...info.map(parts => el('div', '', ...parts.map(([cls, value]) => span(cls, value)))));
    return [el('div', 'res neo', art, facts)];
  }

  const hist = [];
  const COMMANDS = {
    help: () => [text('d', 'commands this terminal knows:'),
      text('', Object.keys(MAN).join('  ')),
      res(span('d', 'try: '), span('g', 'ls -la'), span('d', ' · '), span('g', 'cd projects'), span('d', ' · '),
        span('g', 'cat sca-triage/README.md'), span('d', ' · '), span('g', 'open resume.pdf'), span('d', ' · '), span('g', 'neofetch')),
      text('d', 'Tab completes, ↑ and ↓ recall, Ctrl+C cancels, man <command> explains one')],
    ls, cd, cat, open, tree, neofetch,
    pwd: () => [text('', `/Users/robin${cwd.length ? `/${cwd.join('/')}` : ''}`)],
    whoami: () => [text('', 'robin')],
    id: () => [text('', 'uid=501(robin) gid=20(staff) groups=20(staff),12(everyone),61(localaccounts),80(admin)')],
    hostname: () => [text('', 'dotrobin.local')],
    date: () => { const d = new Date(); return [text('', [stamp(d), zone(d), d.getFullYear()].filter(Boolean).join(' '))]; },
    uname: args => {
      if (args.includes('-a')) return [text('', 'Darwin dotrobin.local 25.0.0 Darwin Kernel Version 25.0.0 arm64')];
      if (args.includes('-m')) return [text('', 'arm64')];
      if (args.includes('-n')) return [text('', 'dotrobin.local')];
      if (args.includes('-r')) return [text('', '25.0.0')];
      return [text('', 'Darwin')];
    },
    echo: args => [text('', args.join(' '))],
    history: () => hist.map((cmd, i) => text('', `${String(i + 1).padStart(5)}  ${cmd}`)),
    man: ([name]) => {
      if (!name) return [err('What manual page do you want?'), err("For example, try 'man man'.")];
      if (!own(MAN, name)) return [err(`No manual entry for ${name}`)];
      const [what, usage] = MAN[name];
      return [text('b', 'NAME'), text('', `     ${name} – ${what}`), text('b', 'SYNOPSIS'), text('', `     ${usage}`)];
    },
    sudo: () => [text('', 'robin is not in the sudoers file. This incident will be reported.'), text('d', '(nice try: this site is read-only)')],
    rm: args => [text('', `rm: ${args.filter(a => !a.startsWith('-'))[0] || 'file'}: Permission denied`), text('d', '(nothing to delete here: this site is read-only)')],
  };

  // ---- the live prompt ----
  const PS = () => {
    const ps = el('span', 'ps', span('pu', 'dotrobin@mac'), ' ', span('pd', show(cwd)), ' %');
    ps.setAttribute('aria-hidden', 'true');
    return ps;
  };
  const input = el('input', '');
  Object.assign(input, { id: 'term-in', type: 'text', maxLength: 200, autocomplete: 'off', spellcheck: false });
  input.setAttribute('autocapitalize', 'off');
  input.setAttribute('autocorrect', 'off');
  input.setAttribute('enterkeyhint', 'send');
  const label = el('label', 'visually-hidden', 'Terminal command. Type a command, then press Enter. Try help. Tab completes once you have typed something.');
  label.htmlFor = 'term-in';
  const cursor = prompt.querySelector('.cur');
  // Only the zsh prompt text is redrawn: moving the input itself would take the keyboard focus away from it.
  const drawPrompt = () => prompt.firstElementChild.replaceWith(PS());
  const complete = el('div', 'term-complete');
  complete.setAttribute('aria-live', 'polite');

  term.classList.add('live');
  const login = out.querySelector('.login');
  if (login) login.replaceWith(lastLogin()); else out.prepend(lastLogin());
  prompt.before(log);
  prompt.after(complete);
  prompt.replaceChildren(PS(), ...(cursor ? [cursor] : []), label, input);
  const hint = document.querySelector('.hint');
  if (hint) hint.hidden = false;

  const toBottom = () => { out.scrollTop = out.scrollHeight; };
  const echo = (typed, suffix = '') => el('p', 'cmd', PS(), ' ', typed + suffix);  // text node: typed text is never HTML

  // Splits on spaces, keeping 'single' and "double" quoted parts together; $NAME expands outside single quotes.
  const words = line => {
    const result = [];
    for (const m of line.matchAll(/'([^']*)'?|"([^"]*)"?|(\S+)/g)) {
      result.push(m[1] !== undefined ? m[1] : expand(m[2] !== undefined ? m[2] : m[3]));
    }
    return result;
  };

  function clearScreen() {
    for (const node of [...out.children]) if (node !== prompt && node !== log && node !== complete) node.remove();
    log.replaceChildren();
    complete.replaceChildren();
  }

  function run(typed) {
    complete.replaceChildren();
    const line = typed.trim();
    if (line) hist.push(line);
    histAt = hist.length;
    const [name, ...args] = words(line);
    if (name === 'clear') { clearScreen(); drawPrompt(); return; }
    const block = el('div', 'entry', echo(typed.replace(/\s+$/, '')));
    if (name === 'exit') {
      block.append(text('', 'logout'), text('d', '[Process completed] Thanks for stopping by.'));
      log.append(block, lastLogin());
      oldpwd = null;
      cwd = [];
    } else if (line) {
      const answer = own(COMMANDS, name) ? COMMANDS[name] : null;
      block.append(...(answer ? answer(args) : [err(`zsh: command not found: ${name}`)]));
      log.append(block);
    } else log.append(block);
    drawPrompt();
    toBottom();
  }

  // ---- tab completion ----
  const names = () => Object.keys(COMMANDS).concat('clear', 'exit').sort();
  function completeInput() {
    const value = input.value;
    const at = value.search(/\S*$/);
    const word = value.slice(at);
    const first = !value.slice(0, at).trim();
    let base = '', options;
    if (first) options = names().map(name => [name, ' ']);
    else {
      const slash = word.lastIndexOf('/');
      base = word.slice(0, slash + 1);
      const found = resolve(base || '.');
      if (!found || !found.node.dir) return;
      options = Object.keys(found.node.entries).sort()
        .filter(key => !key.startsWith('.') || word.slice(slash + 1).startsWith('.'))
        .map(key => [key, found.node.entries[key].dir ? '/' : ' ']);
    }
    const stem = word.slice(base.length);
    const matches = options.filter(([key]) => key.startsWith(stem));
    complete.replaceChildren();
    if (!matches.length) return;
    if (matches.length === 1) {
      input.value = value.slice(0, at) + base + matches[0][0] + matches[0][1];
      return;
    }
    let common = matches[0][0];
    for (const [key] of matches) while (!key.startsWith(common)) common = common.slice(0, -1);
    if (common.length > stem.length) input.value = value.slice(0, at) + base + common;
    complete.append(res(...joinNodes(matches.map(([key, end]) => span(end === '/' ? 'b' : '', key + (end === '/' ? '/' : ''))), '  ')));
    toBottom();
  }

  let histAt = 0;
  let demo = null;
  input.addEventListener('keydown', event => {
    if (event.isComposing) return;
    if (demo) demo.finish();
    const key = event.key;
    if (key === 'Enter') {
      event.preventDefault();
      run(input.value);
      input.value = '';
      prompt.classList.remove('typed');
    } else if (key === 'Tab' && !event.shiftKey && !event.altKey && !event.ctrlKey && !event.metaKey && input.value.trim()) {
      event.preventDefault();  // with nothing typed, Tab moves focus on as usual: no keyboard trap
      completeInput();
    } else if (key === 'ArrowUp' || key === 'ArrowDown') {
      if (!hist.length) return;
      event.preventDefault();
      histAt = key === 'ArrowUp' ? Math.max(0, histAt - 1) : Math.min(hist.length, histAt + 1);
      input.value = histAt < hist.length ? hist[histAt] : '';
      complete.replaceChildren();
    } else if ((event.ctrlKey && !event.metaKey && key.toLowerCase() === 'l') || (event.metaKey && key.toLowerCase() === 'k')) {
      event.preventDefault();
      clearScreen();
    } else if (event.ctrlKey && !event.metaKey && key.toLowerCase() === 'c' && input.selectionStart === input.selectionEnd) {
      event.preventDefault();
      log.append(el('div', 'entry', echo(input.value, '^C')));
      input.value = '';
      histAt = hist.length;
      complete.replaceChildren();
      prompt.classList.remove('typed');
      toBottom();
    } else if (key !== 'Shift') complete.replaceChildren();
  });
  input.addEventListener('input', () => prompt.classList.toggle('typed', input.value !== ''));
  // A tap or click on the window, other than on a link or a text selection, puts the cursor in the prompt.
  term.addEventListener('click', event => {
    if (event.target.closest('a') || String(getSelection())) return;
    input.focus({ preventScroll: true });
    toBottom();
  });

  // ---- ?demo: plays a fixed session for screenshots. Nothing else in the URL is ever read. ----
  if (new URLSearchParams(location.search).has('demo')) {
    const SCRIPT = ['clear', 'neofetch', 'cd projects', 'ls -la', 'cat sca-triage/README.md'];
    const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
    let step = 0, typedChars = 0, timer = 0;
    demo = {
      finish() {
        clearTimeout(timer);
        demo = null;
        if (typedChars) { run(SCRIPT[step]); step += 1; }
        while (step < SCRIPT.length) run(SCRIPT[step++]);
        input.value = '';
        prompt.classList.remove('typed');
      },
    };
    if (still) demo.finish();
    else {
      const tick = () => {
        const command = SCRIPT[step];
        if (typedChars < command.length) {
          typedChars += 1;
          input.value = command.slice(0, typedChars);
          prompt.classList.add('typed');
          timer = setTimeout(tick, 45);
          return;
        }
        run(command);
        input.value = '';
        prompt.classList.remove('typed');
        typedChars = 0;
        step += 1;
        if (step < SCRIPT.length) timer = setTimeout(tick, 500);
        else demo = null;
      };
      timer = setTimeout(tick, 600);
    }
  }
})();
