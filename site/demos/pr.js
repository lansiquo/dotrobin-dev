'use strict';
// sast-triage demo: replays a scan and triage of curated examples (pr-data.json).
// Nothing is scanned in the browser. priority() and the gate mirror analyzers/triage.py.
(async () => {
  try {
    const response = await fetch('pr-data.json?v=triage-1');
    if (!response.ok) throw Error('data');
    const data = await response.json();
    const $ = (id) => document.getElementById(id);
    let current = 0;
    let variant = 'vulnerable';

    function slug(name) {
      return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    }

    function readHash() {
      const raw = decodeURIComponent(location.hash.replace(/^#/, ''));
      if (!raw) return null;
      const [nameSlug, which] = raw.split('/');
      const index = data.findIndex((d) => slug(d.name) === nameSlug);
      if (index < 0) return null;
      if (which === 'proposed-fix') return { index, variant: 'fixed' };
      if (!which || which === 'original') return { index, variant: 'vulnerable' };
      return null;
    }

    function syncHash(push) {
      const next = `#${slug(data[current].name)}/${variant === 'fixed' ? 'proposed-fix' : 'original'}`;
      if (location.hash === next) return;
      history[push ? 'pushState' : 'replaceState'](null, '', next);
    }

    function priority({ severity, code, confidence }) {
      const high = severity === 'CRITICAL' || severity === 'HIGH';
      const testCode = code === 'test';
      let level = high && !testCode ? 1 : high || (severity === 'MEDIUM' && !testCode) ? 2 : 3;
      if (confidence === 'LOW') level = Math.min(level + 1, 3);
      return `P${level}`;
    }

    function annotation(t, p) {
      if (t.new && p === 'P1') return 'failure';
      if (t.new && p === 'P2') return 'warning';
      return 'notice';
    }

    // Plain-language reason for a finding's priority and check annotation.
    function reason(t, p, level) {
      const sev = t.severity.toLowerCase();
      const high = t.severity === 'CRITICAL' || t.severity === 'HIGH';
      const base = high && t.code !== 'test' ? 'P1' : high || (t.severity === 'MEDIUM' && t.code !== 'test') ? 'P2' : 'P3';
      let rank;
      if (high && t.code === 'test') rank = `${titleCase(t.severity)}, but only in test code → ${base}.`;
      else if (base === 'P3') rank = `${titleCase(t.severity)} severity → ${base}.`;
      else rank = `${titleCase(t.severity)} severity in runtime code → ${base}.`;
      if (p !== base) rank += ` Low rule confidence drops it to ${p}.`;
      const outcome = level === 'failure'
        ? 'New, so it fails the check.'
        : t.new
          ? `New, but ${p} only adds a ${level}.`
          : `Pre-existing, so it’s annotated but doesn’t fail the check.`;
      return `${rank} ${outcome}`;
    }

    const titleCase = (s) => s.charAt(0) + s.slice(1).toLowerCase();

    function render() {
      const d = data[current];
      $('category').textContent = d.category + ' · ' + (d.mode === 'scan' ? 'Semgrep example' : 'Behavioral example');
      $('name').textContent = d.name;
      $('impact').textContent = d.impact;
      $('source').textContent = d.sources[variant];
      $('explanation').textContent = variant === 'fixed' ? d.fix : 'Inspect the proposed fix to compare the intended protection.';
      $('limit').textContent = d.limit;
      $('before').setAttribute('aria-pressed', String(variant === 'vulnerable'));
      $('after').setAttribute('aria-pressed', String(variant === 'fixed'));
      $('result').hidden = true;
      [...$('choices').children].forEach((b, i) => b.setAttribute('aria-pressed', String(i === current)));
      [...$('triage-rows').children].forEach((r) => r.classList.toggle('selected', Number(r.dataset.index) === current));
    }

    function select(i, nextVariant = 'vulnerable') {
      current = i;
      variant = nextVariant;
      render();
    }

    function renderTriage() {
      const rows = $('triage-rows');
      rows.replaceChildren();
      const blocking = [];
      data.forEach((d, i) => {
        const t = d.triage;
        const p = priority(t);
        const level = annotation(t, p);
        if (level === 'failure') blocking.push(d.name);
        const tr = document.createElement('tr');
        const first = document.createElement('td');
        const open = document.createElement('button');
        open.type = 'button';
        open.className = 'link-button';
        open.textContent = `${d.category.split(' ')[0]} ${d.name}`;
        open.addEventListener('click', () => {
          select(i);
          syncHash(true);
          $('examples').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
        });
        const kind = document.createElement('span');
        kind.className = 'evidence-badge';
        kind.textContent = d.mode === 'scan' ? 'Semgrep example' : 'Behavioral example';
        first.append(open, kind);
        tr.append(first);
        const cells = [
          `${t.file}:${t.line}`,
          titleCase(t.severity) + (t.confidence === 'LOW' ? ' · low confidence' : ''),
          t.code === 'test' ? 'Test' : 'Runtime',
          t.new ? 'New' : 'Pre-existing',
          p,
        ];
        for (const text of cells) {
          const td = document.createElement('td');
          td.textContent = text;
          tr.append(td);
        }
        const badge = document.createElement('td');
        const span = document.createElement('span');
        span.className = `badge badge-${level}`;
        span.textContent = level === 'failure' ? 'Fails check' : level === 'warning' ? 'Warning' : 'Notice';
        badge.append(span);
        tr.append(badge);
        const whyRow = document.createElement('tr');
        whyRow.className = 'why-row';
        const why = document.createElement('td');
        why.colSpan = 7;
        const whyText = document.createElement('span');
        whyText.className = 'why-text';
        whyText.textContent = `Why: ${reason(t, p, level)}`;
        why.append(whyText);
        whyRow.append(why);
        tr.dataset.index = whyRow.dataset.index = String(i);
        rows.append(tr, whyRow);
      });
      const gate = $('gate');
      if (blocking.length) {
        gate.className = 'gate gate-fail';
        gate.textContent = `Gate: FAIL — ${blocking.length} new P1 finding${blocking.length === 1 ? '' : 's'} (${blocking.join(', ')}). Pre-existing and lower-priority findings are annotated but don’t fail the check.`;
      } else {
        gate.className = 'gate gate-pass';
        gate.textContent = 'Gate: PASS — no new P1 findings.';
      }
      $('triage-output').hidden = false;
      render();
    }

    async function runScan() {
      const button = $('run-scan');
      const status = $('scan-status');
      const delay = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 650;
      const wait = () => new Promise((r) => setTimeout(r, delay));
      button.disabled = true;
      button.textContent = 'Running demo';
      $('triage-output').hidden = true;
      try {
        for (const step of [
          'Simulated pull request #42 · 10 curated examples, not a live fetch.',
          'Replaying four saved Semgrep examples.',
          'Replaying six saved behavioral examples.',
          'Applying the saved new and pre-existing labels.',
        ]) {
          status.textContent = step;
          await wait();
        }
        status.textContent = 'Replay complete: 10 curated examples. Nothing was scanned.';
        renderTriage();
        button.disabled = false;
        button.textContent = 'Replay demo';
      } catch (e) {
        if (status) status.textContent = 'The saved demo did not finish. Nothing was scanned.';
        button.disabled = false;
        button.textContent = 'Run demo';
      }
    }

    data.forEach((d, i) => {
      const b = document.createElement('button');
      b.textContent = d.category + ' · ' + d.name;
      b.addEventListener('click', () => { select(i); syncHash(true); });
      $('choices').append(b);
    });
    $('before').onclick = () => { variant = 'vulnerable'; render(); syncHash(true); };
    $('after').onclick = () => { variant = 'fixed'; render(); syncHash(true); };
    $('inspect').onclick = () => {
      $('result').textContent = data[current].explanations[variant];
      $('result').hidden = false;
    };
    $('run-scan').onclick = runScan;
    const initial = readHash();
    if (initial) select(initial.index, initial.variant);
    else render();
    if (initial) $('examples').scrollIntoView({ behavior: 'auto', block: 'start' });
    window.addEventListener('popstate', () => {
      const next = readHash();
      if (next) select(next.index, next.variant);
      else select(0);
      $('examples').scrollIntoView({ behavior: 'auto', block: 'start' });
    });
    $('app').hidden = false;
  } catch (e) {
    document.getElementById('load-error').hidden = false;
  }
})();
