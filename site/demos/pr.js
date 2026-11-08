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
      let raw;
      try {
        raw = decodeURIComponent(location.hash.replace(/^#/, ''));
      } catch {
        return null; // Malformed percent-encoding: treat it as no saved example.
      }
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

    // Triage replay. The table is built once per run, then each step fills in
    // the part of the page it describes, so the page always matches the step list.
    const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
    const scanCount = data.filter((d) => d.mode === 'scan').length;
    const behavioralCount = data.length - scanCount;
    let rowRefs = [];
    let runId = 0; // Bumped by Reset, so an older run stops at its next step.
    let state = 'idle'; // idle | running | done

    function pendingCell() {
      const td = document.createElement('td');
      td.className = 'cell-pending';
      td.textContent = '—';
      return td;
    }

    function fillCell(td, text, child) {
      td.className = 'cell-filled';
      td.replaceChildren(child || document.createTextNode(text));
    }

    function buildTriage() {
      const rows = $('triage-rows');
      rows.replaceChildren();
      rowRefs = data.map((d, i) => {
        const t = d.triage;
        const p = priority(t);
        const level = annotation(t, p);
        const tr = document.createElement('tr');
        tr.hidden = true;
        const first = document.createElement('td');
        const open = document.createElement('button');
        open.type = 'button';
        open.className = 'link-button';
        open.textContent = `${d.category.split(' ')[0]} ${d.name}`;
        open.addEventListener('click', () => {
          select(i);
          syncHash(true);
          $('examples').scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth' });
        });
        const kind = document.createElement('span');
        kind.className = 'evidence-badge';
        kind.textContent = d.mode === 'scan' ? 'Semgrep example' : 'Behavioral example';
        first.append(open, kind);
        tr.append(first);
        for (const text of [
          `${t.file}:${t.line}`,
          titleCase(t.severity) + (t.confidence === 'LOW' ? ' · low confidence' : ''),
          t.code === 'test' ? 'Test' : 'Runtime',
        ]) {
          const td = document.createElement('td');
          td.textContent = text;
          tr.append(td);
        }
        const status = pendingCell();
        const prio = pendingCell();
        const note = pendingCell();
        tr.append(status, prio, note);
        const whyRow = document.createElement('tr');
        whyRow.className = 'why-row';
        whyRow.hidden = true;
        const why = document.createElement('td');
        why.colSpan = 7;
        const whyText = document.createElement('span');
        whyText.className = 'why-text';
        whyText.textContent = `Why: ${reason(t, p, level)}`;
        why.append(whyText);
        whyRow.append(why);
        tr.dataset.index = whyRow.dataset.index = String(i);
        rows.append(tr, whyRow);
        return { d, t, p, level, tr, whyRow, status, prio, note };
      });
      const gate = $('gate');
      gate.className = 'gate gate-pending';
      gate.textContent = 'Gate: waiting for the triage steps to finish.';
      render();
    }

    function showRows(mode) {
      for (const r of rowRefs) {
        if (r.d.mode !== mode) continue;
        r.tr.hidden = false;
        r.tr.classList.add('row-in');
      }
    }

    function fillStatus() {
      for (const r of rowRefs) fillCell(r.status, r.t.new ? 'New' : 'Pre-existing');
    }

    function fillPriority() {
      for (const r of rowRefs) fillCell(r.prio, r.p);
    }

    function decide() {
      const blocking = [];
      for (const r of rowRefs) {
        const span = document.createElement('span');
        span.className = `badge badge-${r.level}`;
        span.textContent = r.level === 'failure' ? 'Fails check' : r.level === 'warning' ? 'Warning' : 'Notice';
        fillCell(r.note, '', span);
        r.whyRow.hidden = false;
        if (r.level === 'failure') blocking.push(r.d.name);
      }
      const gate = $('gate');
      if (blocking.length) {
        gate.className = 'gate gate-fail';
        gate.textContent = `Gate: FAIL — ${blocking.length} new P1 finding${blocking.length === 1 ? '' : 's'} (${blocking.join(', ')}). Pre-existing and lower-priority findings are annotated but don’t fail the check.`;
      } else {
        gate.className = 'gate gate-pass';
        gate.textContent = 'Gate: PASS — no new P1 findings.';
      }
    }

    const steps = [
      {
        label: 'Open pull request #42',
        status: `Opening simulated pull request #42 with ${data.length} curated examples. Nothing is fetched.`,
        apply: () => { buildTriage(); $('triage-output').hidden = false; },
      },
      {
        label: `Replay ${scanCount} Semgrep findings`,
        status: `Adding the ${scanCount} saved Semgrep findings to the table.`,
        apply: () => showRows('scan'),
      },
      {
        label: `Replay ${behavioralCount} behavioral findings`,
        status: `Adding the ${behavioralCount} saved behavioral test results to the table.`,
        apply: () => showRows('behavioral'),
      },
      {
        label: 'Label new or pre-existing',
        status: 'Labelling each finding: is it on a line this pull request changed?',
        apply: fillStatus,
      },
      {
        label: 'Rank P1–P3',
        status: 'Ranking each finding by severity, runtime or test code, and rule confidence.',
        apply: fillPriority,
      },
      {
        label: 'Decide the check',
        status: 'Annotating each finding and deciding whether the check fails.',
        apply: decide,
      },
    ];

    function stepItems() {
      return [...$('run-steps').children];
    }

    function setStep(active) {
      stepItems().forEach((li, i) => {
        li.className = i < active ? 'is-done' : i === active ? 'is-active' : 'is-pending';
        if (i === active) li.setAttribute('aria-current', 'step');
        else li.removeAttribute('aria-current');
      });
    }

    function setControls(next, detail) {
      state = next;
      const button = $('run-scan');
      button.disabled = next === 'running';
      $('run-icon').textContent = next === 'done' ? '↻' : '▶';
      $('run-label').textContent = next === 'running' ? `Running… ${detail}` : next === 'done' ? 'Run again' : 'Run demo';
      $('reset-scan').hidden = next === 'idle';
      $('reset-scan').textContent = next === 'running' ? 'Stop and reset' : 'Reset';
    }

    function resetDemo() {
      runId += 1;
      setStep(-1);
      $('triage-output').hidden = true;
      $('triage-rows').replaceChildren();
      rowRefs = [];
      $('scan-status').textContent = '';
      setControls('idle');
    }

    async function runScan() {
      if (state === 'running') return;
      if (state === 'done') resetDemo();
      const id = ++runId;
      const delay = reducedMotion() ? 0 : 800;
      const wait = () => new Promise((r) => setTimeout(r, delay));
      const status = $('scan-status');
      try {
        for (let i = 0; i < steps.length; i += 1) {
          setControls('running', `step ${i + 1} of ${steps.length}`);
          setStep(i);
          status.textContent = steps[i].status;
          steps[i].apply();
          await wait();
          if (id !== runId) return; // Reset was pressed.
        }
        setStep(steps.length);
        status.textContent = `Replay complete: ${data.length} curated examples. Nothing was scanned.`;
        setControls('done');
      } catch (e) {
        if (id !== runId) return;
        status.textContent = 'The saved demo did not finish. Nothing was scanned.';
        setControls('done');
      }
    }

    steps.forEach((step) => {
      const li = document.createElement('li');
      li.className = 'is-pending';
      li.textContent = step.label;
      $('run-steps').append(li);
    });
    $('reset-scan').onclick = () => {
      resetDemo();
      $('run-scan').focus();
    };

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
      if (next) {
        select(next.index, next.variant);
        $('examples').scrollIntoView({ behavior: 'auto', block: 'start' });
      } else {
        // Back to an entry with no saved example: reset the selection and let
        // the browser restore that entry's scroll position.
        select(0);
      }
    });
    $('app').hidden = false;
  } catch (e) {
    document.getElementById('load-error').hidden = false;
  }
})();
