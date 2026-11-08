'use strict';
// sca-triage demo: replays one recorded sca-triage run (sca-data.json).
// Nothing is installed or scanned in the browser. Every sentence below is
// built from the recorded data, so the page can't drift from the run it shows.
(() => {
  const $ = (id) => document.getElementById(id);
  const SIDES = ['before', 'after'];
  const VIEWS = ['audit', 'security', 'regression'];
  const REACH = {
    imported: 'Imported by the app',
    'via-imported': 'Pulled in by an imported dependency',
    'test-only': 'Test code only',
    'not-imported': 'Not imported',
  };
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const list = (items) =>
    items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;

  // Reject data that doesn't have the shape the page relies on, with a reason.
  function validate(d) {
    const isCount = (n) => Number.isInteger(n) && n >= 0;
    const fail = (why) => { throw new Error(`Recorded data is incomplete (${why}).`); };
    if (!d || typeof d !== 'object') fail('not an object');
    if (!Array.isArray(d.packages) || !d.packages.length) fail('no packages');
    d.packages.forEach((p, i) => {
      const where = `package ${i + 1}`;
      for (const k of ['name', 'before', 'after', 'priority', 'severity']) {
        if (typeof p[k] !== 'string' || !p[k]) fail(`${where}: ${k}`);
      }
      if (!/^P[1-3]$/.test(p.priority)) fail(`${where}: priority`);
      if (!isCount(p.advisories)) fail(`${where}: advisories`);
      if (!(p.reachability in REACH)) fail(`${where}: reachability`);
    });
    for (const side of SIDES) {
      const s = d.summary?.[side];
      const t = d.tests?.[side];
      const f = d.tests?.functional?.[side];
      if (!s || !['P1', 'P2', 'P3', 'advisories', 'vulnerable'].every((k) => isCount(s[k]))) fail(`summary.${side}`);
      if (!t || !isCount(t.passed) || !isCount(t.total) || t.passed > t.total) fail(`tests.${side}`);
      if (!f || !isCount(f.passed) || !isCount(f.total) || f.passed > f.total) fail(`functional tests.${side}`);
      if (!['pass', 'fail'].includes(d.tests?.security?.[side])) fail(`security test.${side}`);
      if (!['pass', 'fail'].includes(d.gate?.[side])) fail(`gate.${side}`);
    }
    if (typeof d.gate.failOn !== 'string') fail('gate.failOn');
    return d;
  }

  async function loadData() {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    try {
      const r = await fetch('sca-data.json?v=3', { signal: controller.signal, cache: 'no-cache' });
      if (!r.ok) throw new Error(`The recorded data could not be loaded (HTTP ${r.status}).`);
      return validate(await r.json());
    } catch (e) {
      if (e.name === 'AbortError') throw new Error('The recorded data took too long to load.');
      if (e instanceof SyntaxError) throw new Error('The recorded data file is not valid JSON.');
      throw e;
    } finally {
      clearTimeout(timer);
    }
  }

  function start(d) {
    let side = 'before';
    let view = 'audit';
    const gate = d.gate.failOn;
    const exploited = d.packages.filter((p) => p.exploitDemonstrated);
    const majors = d.packages.filter((p) => p.majorUpgrade);
    const unreachedSevere = d.packages.filter(
      (p) => p.reachability === 'not-imported' && /^(critical|high)$/i.test(p.severity) && p.priority !== 'P1',
    );

    // "#after/security" style links, read defensively.
    function readHash() {
      let raw;
      try {
        raw = decodeURIComponent(location.hash.replace(/^#/, ''));
      } catch {
        return null;
      }
      const [s, v] = raw.split('/');
      if (!SIDES.includes(s)) return null;
      return { side: s, view: VIEWS.includes(v) ? v : 'audit' };
    }

    function syncHash(push) {
      const next = `#${side}/${view}`;
      if (location.hash === next) return;
      history[push ? 'pushState' : 'replaceState'](null, '', next);
    }

    function auditText() {
      const s = d.summary[side];
      const gateResult = d.gate[side] === 'pass' ? 'passed' : 'failed';
      if (side === 'before') {
        const ranks = ['P1', 'P2', 'P3'].filter((p) => s[p]).map((p) => `${p}: ${s[p]}`).join(', ');
        let text = `Recorded scan: ${plural(s.vulnerable, 'vulnerable package', 'vulnerable packages')} and ${plural(s.advisories, 'advisory', 'advisories')}. Ranked ${ranks || 'none'}.`;
        if (unreachedSevere.length) {
          const names = list(unreachedSevere.map((p) => `${p.name} (${p.severity.toLowerCase()})`));
          text += ` ${names} ${unreachedSevere.length === 1 ? 'ranks' : 'rank'} below P1 because nothing in the app imports ${unreachedSevere.length === 1 ? 'it' : 'them'}.`;
        }
        return `${text} The ${gate} gate ${gateResult}.`;
      }
      let text = `Recorded rescan after the upgrades: ${plural(s.vulnerable, 'vulnerable package', 'vulnerable packages')}. The ${gate} gate ${gateResult}. This reflects the advisory database at scan time; zero findings is not a security certification.`;
      if (majors.length) {
        const names = list(majors.map((p) => `${p.name} ${p.before} → ${p.after}`));
        text += ` ${names} ${majors.length === 1 ? 'is a major upgrade' : 'are major upgrades'}, flagged for release-note review. The saved tests cover the app’s own behavior.`;
      }
      return text;
    }

    function securityText() {
      const name = d.tests.security.name;
      const result = d.tests.security[side];
      const pkg = exploited.length ? list(exploited.map((p) => p.name)) : 'the vulnerable dependency';
      const at = (key) => (exploited.length ? list(exploited.map((p) => `${p.name} ${p[key]}`)) : pkg);
      if (side === 'before') {
        return result === 'fail'
          ? `Recorded security test FAILED, as expected, with ${at('before')}: “${name}”. This is the advisory the lab proves end to end. The test shows the vulnerable behavior with a harmless marker; no code execution or data theft is claimed.`
          : `Recorded security test passed with ${at('before')}: “${name}”.`;
      }
      return result === 'pass'
        ? `Recorded security test PASSED after upgrading to ${at('after')}: the same untrusted input no longer triggers the vulnerable behavior (“${name}”).`
        : `Recorded security test still FAILED after upgrading to ${at('after')}: “${name}”.`;
    }

    function regressionText() {
      const t = d.tests[side];
      const f = d.tests.functional[side];
      let text = `Recorded tests: ${t.passed} of ${t.total} passed, including ${f.passed} of ${f.total} functional tests.`;
      const fb = d.tests.functional.before;
      const fa = d.tests.functional.after;
      const functionalAlwaysPass = fb.passed === fb.total && fa.passed === fa.total;
      if (functionalAlwaysPass && d.tests.security.before === 'fail') {
        text += ' The functional tests pass on both versions, which is why compatibility tests alone miss this defect; the security test is what catches it.';
      }
      return text;
    }

    function renderEvidence() {
      const texts = { audit: auditText, security: securityText, regression: regressionText };
      $('evidence-detail').textContent = texts[view]();
    }

    function render() {
      $('before').setAttribute('aria-pressed', String(side === 'before'));
      $('after').setAttribute('aria-pressed', String(side === 'after'));
      $('evidence').value = view;

      const s = d.summary[side];
      const t = d.tests[side];
      const passed = d.gate[side] === 'pass';
      const gateBox = $('sca-gate');
      gateBox.className = `gate ${passed ? 'gate-pass' : 'gate-fail'}`;
      gateBox.textContent = passed
        ? `Gate: PASS — no ${gate} findings ${side === 'after' ? 'after the upgrades' : ''}.`.replace(' .', '.')
        : `Gate: FAIL — ${plural(s[gate] ?? 0, `${gate} finding`, `${gate} findings`)} in code the app loads.`;

      $('metrics').replaceChildren();
      for (const [value, label] of [
        [s.vulnerable, 'vulnerable packages'],
        [s[gate] ?? 0, `${gate} findings (gate)`],
        [`${t.passed}/${t.total}`, 'tests passed'],
      ]) {
        const box = document.createElement('div');
        box.className = 'metric';
        const strong = document.createElement('strong');
        strong.textContent = value;
        const caption = document.createElement('span');
        caption.textContent = label;
        box.append(strong, caption);
        $('metrics').append(box);
      }

      $('packages-caption').textContent =
        `${plural(d.packages.length, 'dependency', 'dependencies')} with findings` +
        (Number.isInteger(d.packagesScanned) ? ` out of ${d.packagesScanned} packages scanned` : '') +
        ' · recorded results';

      const cleanAfter = d.summary.after.vulnerable === 0;
      $('packages').replaceChildren();
      for (const p of d.packages) {
        const row = document.createElement('tr');
        const version = side === 'before'
          ? `${p.before} · ${p.severity.toLowerCase()}, ${plural(p.advisories, 'advisory', 'advisories')}`
          : `${p.after}${p.majorUpgrade ? ' (major upgrade)' : ''}`;
        const reach = side === 'before'
          ? `${p.priority} · ${REACH[p.reachability]}${p.exploitDemonstrated ? ', exploit demonstrated' : ''}`
          : cleanAfter ? 'No known advisories' : 'See the recorded rescan';
        for (const text of [p.name, version, reach]) {
          const td = document.createElement('td');
          td.textContent = text;
          row.append(td);
        }
        $('packages').append(row);
      }
      renderEvidence();
    }

    function setSide(next) {
      if (next === side) return;
      side = next;
      render();
      syncHash(true);
    }

    $('before').onclick = () => setSide('before');
    $('after').onclick = () => setSide('after');
    $('evidence').onchange = () => {
      view = VIEWS.includes($('evidence').value) ? $('evidence').value : 'audit';
      renderEvidence();
      syncHash(false);
    };
    window.addEventListener('popstate', () => {
      const next = readHash() || { side: 'before', view: 'audit' };
      side = next.side;
      view = next.view;
      render();
    });

    const initial = readHash();
    if (initial) ({ side, view } = initial);
    render();
    $('app').hidden = false;
  }

  async function boot() {
    $('load-error').hidden = true;
    $('loading').hidden = false;
    try {
      start(await loadData());
    } catch (e) {
      $('load-error-detail').textContent = e instanceof Error && e.message ? e.message : 'The demo could not start.';
      $('load-error').hidden = false;
    } finally {
      $('loading').hidden = true;
    }
  }

  $('retry').onclick = boot;
  boot();
})();
