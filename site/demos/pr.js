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

    const titleCase = (s) => s.charAt(0) + s.slice(1).toLowerCase();

    function render() {
      const d = data[current];
      $('category').textContent = d.category + ' · ' + (d.mode === 'scan' ? 'Static analysis example' : 'Behavior test example');
      $('name').textContent = d.name;
      $('impact').textContent = d.impact;
      $('source').textContent = d.sources[variant];
      $('explanation').textContent = variant === 'fixed' ? d.fix : 'Inspect the proposed fix to compare the intended protection.';
      $('limit').textContent = d.limit;
      $('before').setAttribute('aria-pressed', String(variant === 'vulnerable'));
      $('after').setAttribute('aria-pressed', String(variant === 'fixed'));
      $('result').hidden = true;
      [...$('choices').children].forEach((b, i) => b.setAttribute('aria-pressed', String(i === current)));
      [...$('triage-rows').children].forEach((r, i) => r.classList.toggle('selected', i === current));
    }

    function select(i) {
      current = i;
      variant = 'vulnerable';
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
          $('examples').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
        });
        first.append(open);
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
        rows.append(tr);
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
      $('triage-output').hidden = true;
      for (const step of [
        'Fetching pull request #42 · 10 changed files…',
        'Running Semgrep rules on changed files…',
        'Running behavioral checks…',
        'Comparing findings with the base branch…',
      ]) {
        status.textContent = `Replay: ${step}`;
        await wait();
      }
      status.textContent = 'Replay complete: 10 findings triaged.';
      renderTriage();
      button.disabled = false;
      button.textContent = 'Run scan again';
    }

    data.forEach((d, i) => {
      const b = document.createElement('button');
      b.textContent = d.category + ' · ' + d.name;
      b.addEventListener('click', () => select(i));
      $('choices').append(b);
    });
    $('before').onclick = () => { variant = 'vulnerable'; render(); };
    $('after').onclick = () => { variant = 'fixed'; render(); };
    $('inspect').onclick = () => {
      $('result').textContent = data[current].explanations[variant];
      $('result').hidden = false;
    };
    $('run-scan').onclick = runScan;
    render();
    $('app').hidden = false;
  } catch (e) {
    document.getElementById('load-error').hidden = false;
  }
})();
