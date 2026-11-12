// Release pulse: a heartbeat line in the header. Each beat is one published release of
// sast-triage or sca-triage in the last 7 days, read from data/pulse.json on this site.
// The line draws once and then holds still. Without JavaScript the static line in the page stays.
(() => {
  'use strict';
  const root = document.querySelector('.pulse');
  const stage = root && root.querySelector('.pulse-stage');
  if (!stage || typeof fetch !== 'function' || typeof ResizeObserver !== 'function') return;

  const NS = 'http://www.w3.org/2000/svg', DAY = 864e5, WEEK = 7 * DAY;
  const PAD = 56;   // room right of "now" for the label centred under the live dot
  // One beat as [offset, height] pairs, in beat half-widths: small dip, spike, overshoot, back to the baseline.
  const SHAPE = [[-1, 0], [-.67, .08], [-.39, .14], [0, -1], [.39, .16], [.72, .05], [1, 0]];
  const weekday = new Intl.DateTimeFormat('en-GB', { weekday: 'short' });
  const stamp = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });

  const fill = (node, attrs, children) => { for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v); node.append(...children); return node; };
  const el = (tag, attrs = {}, ...children) => fill(document.createElement(tag), attrs, children);
  const svg = (tag, attrs = {}, ...children) => fill(document.createElementNS(NS, tag), attrs, children);
  const round = v => Math.round(v * 10) / 10;
  const countText = n => `${n} release${n === 1 ? '' : 's'} this week`;

  function ago(ms) {
    const minutes = Math.floor(ms / 6e4);
    if (minutes < 1) return 'moments ago';
    if (minutes < 60) return `${minutes}m ago`;
    if (minutes < 48 * 60) return `${Math.floor(minutes / 60)}h ago`;
    return `${Math.floor(minutes / 1440)}d ago`;
  }
  function shape(d) {
    for (let i = 1; i < SHAPE.length; i++) {
      const [x0, y0] = SHAPE[i - 1], [x1, y1] = SHAPE[i];
      if (d >= x0 && d <= x1) return y0 + (y1 - y0) * (d - x0) / (x1 - x0);
    }
    return 0;
  }
  // A fixed faint tremor on the baseline. The same width always gives the same line.
  const tremor = i => { const v = Math.sin(i * 12.9898) * 43758.5453; return (v - Math.floor(v) - .5) * 2.2; };

  function layout(w, h, now, releases) {
    const end = Math.max(PAD, w - PAD), base = h - 50, top = 22;
    // Half-width of one beat. It is also the closest two beats may sit, so releases minutes apart stay separate beats.
    const reach = Math.max(5.5, Math.min(9, end / 60));
    const beats = releases.filter(r => r.time > now - WEEK && r.time <= now).map(r => {
      const age = (now - r.time) / WEEK;
      return { ...r, x: end - age * end, amp: (base - top) * (.3 + .7 * Math.pow(1 - age, 2)) }; // recent beats are taller
    });
    for (let i = 1; i < beats.length; i++) beats[i].x = Math.max(beats[i].x, beats[i - 1].x + reach);
    for (let i = beats.length - 1; i >= 0; i--) beats[i].x = Math.min(beats[i].x, i === beats.length - 1 ? end - reach - 2 : beats[i + 1].x - reach);
    const xs = new Set([end]);
    for (let x = 0; x < end; x += 1.5) xs.add(x);
    for (const b of beats) for (const [d] of SHAPE) if (b.x + d * reach >= 0 && b.x + d * reach <= end) xs.add(b.x + d * reach);
    const points = [...xs].sort((a, b) => a - b).map(x => {
      let y = base + (x === end ? 0 : tremor(Math.round(x / 1.5)));
      for (const b of beats) if (Math.abs(x - b.x) <= reach) y += b.amp * shape((x - b.x) / reach);
      return round(x) + ' ' + round(y);
    });
    return { end, base, beats, path: 'M' + points.join('L') };
  }

  const count = el('p', { class: 'pulse-count' });
  const latest = el('p', { class: 'pulse-latest' });
  const tip = el('div', { class: 'pulse-tip', 'aria-hidden': 'true', hidden: '' }, el('b'), el('span'));
  let data = null, art = null, group = null, view = null, shown = -1;

  function show(i) {
    const b = view.beats[i];
    if (!b) return;
    shown = i;
    tip.firstChild.textContent = `${b.tool} ${b.version}`;
    tip.lastChild.textContent = stamp.format(b.time);
    tip.hidden = false;
    const half = tip.offsetWidth / 2;
    tip.style.top = (view.base + 18) + 'px';
    tip.style.left = round(Math.min(Math.max(b.x, half), Math.max(half, stage.clientWidth - half))) + 'px';
  }
  function hide() { shown = -1; tip.hidden = true; }
  const focused = () => group ? [...group.children].indexOf(document.activeElement) : -1;
  function moveTo(i) {
    const buttons = [...group.children];
    if (!buttons[i]) return;
    for (const b of buttons) b.tabIndex = -1;
    buttons[i].tabIndex = 0;
    buttons[i].focus();
  }
  function onKey(event) {
    const i = focused(), last = group.children.length - 1;
    const next = { ArrowLeft: i - 1, ArrowRight: i + 1, Home: 0, End: last }[event.key];
    if (event.key === 'Escape') hide();
    if (i < 0 || next === undefined) return;
    event.preventDefault();
    moveTo(Math.min(Math.max(next, 0), last));
  }

  function now() { return Math.max(Date.now(), data.generated, data.latest ? data.latest.time : 0); }
  function label() { latest.textContent = data.latest ? `${data.latest.version} · ${ago(now() - data.latest.time)}` : ''; }

  function render() {
    const w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    const t = now(), keep = focused();
    view = layout(w, h, t, data.releases);
    const step = view.end / 14, grid = [], days = [];
    for (let k = 0; k <= 14; k++) grid.push(svg('line', { class: 'pulse-grid', x1: round(view.end - k * step), x2: round(view.end - k * step), y1: 8, y2: h - 20 }));
    for (let k = 0; k < 7; k++) days.push(svg('text', { class: 'pulse-day', x: round(view.end - k * step * 2), y: h - 4, 'text-anchor': 'middle' }, weekday.format(t - k * DAY)));
    const next = svg('svg', { class: 'pulse-svg', viewBox: `0 0 ${w} ${h}`, 'aria-hidden': 'true', focusable: 'false' },
      svg('defs', {},
        svg('linearGradient', { id: 'pulse-stroke', gradientUnits: 'userSpaceOnUse', x1: 0, x2: view.end, y1: 0, y2: 0 },
          svg('stop', { offset: 0, 'stop-color': '#baa0ff', 'stop-opacity': 0 }), svg('stop', { offset: .06, 'stop-color': '#baa0ff', 'stop-opacity': .3 }),
          svg('stop', { offset: .7, 'stop-color': '#baa0ff', 'stop-opacity': .9 }), svg('stop', { offset: 1, 'stop-color': '#d9ccff' })),
        svg('filter', { id: 'pulse-glow', filterUnits: 'userSpaceOnUse', x: -20, y: -20, width: w + 40, height: h + 40 },
          svg('feGaussianBlur', { stdDeviation: 2.5, result: 'b' }), svg('feMerge', {}, svg('feMergeNode', { in: 'b' }), svg('feMergeNode', { in: 'SourceGraphic' })))),
      ...grid,
      svg('path', { class: 'pulse-line', d: view.path, pathLength: 1, stroke: 'url(#pulse-stroke)', filter: 'url(#pulse-glow)' }),
      ...days,
      svg('circle', { class: 'pulse-ring', cx: view.end, cy: view.base, r: 12 }),
      svg('circle', { class: 'pulse-dot', cx: view.end, cy: view.base, r: 5, filter: 'url(#pulse-glow)' }));

    const buttons = view.beats.map((b, i) => {
      const before = view.beats[i - 1], after = view.beats[i + 1];
      const left = Math.max(before ? (before.x + b.x) / 2 : 0, b.x - 22, 0), right = Math.min(after ? (b.x + after.x) / 2 : w, b.x + 22, w);
      const button = el('button', { type: 'button', class: 'pulse-beat', tabindex: i === view.beats.length - 1 ? '0' : '-1', 'aria-label': `${b.tool} ${b.version}, released ${stamp.format(b.time)}` });
      button.style.left = round(left) + 'px';
      button.style.width = round(right - left) + 'px';
      button.style.height = (view.base + 16) + 'px';
      button.addEventListener('mouseenter', () => show(i));
      button.addEventListener('mouseleave', () => { const f = focused(); if (f >= 0) show(f); else hide(); });
      button.addEventListener('focus', () => show(i));
      button.addEventListener('blur', hide);
      button.addEventListener('click', () => { moveTo(i); show(i); });
      return button;
    });
    const nextGroup = el('div', { class: 'pulse-beats', role: 'group', 'aria-label': `${countText(view.beats.length)}. Left and right arrow keys move between releases.` }, ...buttons);
    nextGroup.addEventListener('keydown', onKey);

    hide();
    if (art) art.remove();
    if (group) group.remove();
    art = next; group = nextGroup;
    stage.prepend(art);
    tip.before(group);
    stage.style.setProperty('--pulse-base', view.base + 'px');
    count.textContent = countText(view.beats.length);
    label();
    if (keep >= 0 && buttons.length) moveTo(Math.min(keep, buttons.length - 1));
  }

  fetch('data/pulse.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : Promise.reject(new Error('pulse data'))).then(json => {
    const releases = (Array.isArray(json.releases) ? json.releases : [])
      .map(r => ({ tool: String(r.tool), version: String(r.version), time: Date.parse(r.published) }))
      .filter(r => Number.isFinite(r.time)).sort((a, b) => a.time - b.time);
    data = { releases, latest: releases[releases.length - 1] || null, generated: Date.parse(json.generated) || 0 };
    stage.append(count, latest, tip);
    root.dataset.ready = '';
    new ResizeObserver(render).observe(stage);
    // After the first draw the line is still; later redraws (a resized window) appear already drawn.
    setTimeout(() => root.classList.add('pulse-still'), 2400);
    setInterval(label, 30000);
    document.addEventListener('pointerdown', event => { if (shown >= 0 && !event.target.closest('.pulse-beat')) hide(); });
  }).catch(() => {});
})();
