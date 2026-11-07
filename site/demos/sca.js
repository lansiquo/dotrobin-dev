'use strict';
// sca-triage demo: replays one recorded sca-triage run (sca-data.json).
// Nothing is installed or scanned in the browser.
(async () => {
  try {
    const r = await fetch('sca-data.json?v=3');
    if (!r.ok) throw Error('data');
    const d = await r.json();
    const $ = (id) => document.getElementById(id);
    const date = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' }).format(new Date(d.captured));
    const REACH = {
      imported: 'Imported by the app',
      'via-imported': 'Pulled in by an imported dependency',
      'test-only': 'Test code only',
      'not-imported': 'Not imported',
    };
    let side = 'before';

    function evidence() {
      const s = d.summary[side];
      const t = d.tests[side];
      const f = d.tests.functional[side];
      const texts = {
        audit:
          side === 'before'
            ? `Recorded scan: ${s.vulnerable} vulnerable packages and ${s.advisories} advisories. Ranked P1: ${s.P1}, P2: ${s.P2}. tar has critical advisories but ranks P2 because nothing in the app imports it. The P1 gate failed.`
            : `Recorded rescan after the upgrades: ${s.vulnerable} vulnerable packages. The P1 gate passed. This reflects the advisory database on ${date}, not a security certification.`,
        security:
          side === 'before'
            ? `Recorded security test FAILED, as expected: untrusted option tokens made minimist place a harmless marker on Function.prototype. This is the one advisory the lab proves end to end; no code execution or data theft is claimed.`
            : `Recorded security test PASSED: the same input no longer pollutes Function.prototype after the minimist upgrade.`,
        regression: `Recorded tests: ${t.passed} of ${t.total} passed, including ${f.passed} of ${f.total} functional tests. The functional tests pass on both versions, which is why compatibility tests alone miss this defect.`,
      };
      $('evidence-detail').textContent = texts[$('evidence').value];
    }

    function render() {
      $('before').setAttribute('aria-pressed', String(side === 'before'));
      $('after').setAttribute('aria-pressed', String(side === 'after'));

      const s = d.summary[side];
      const t = d.tests[side];
      $('metrics').replaceChildren();
      for (const [value, label] of [
        [s.vulnerable, 'vulnerable packages'],
        [s.P1, 'P1 findings (gate)'],
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

      $('packages').replaceChildren();
      for (const p of d.packages) {
        const row = document.createElement('tr');
        const version = side === 'before' ? `${p.before} · ${p.severity}, ${p.advisories} advisor${p.advisories === 1 ? 'y' : 'ies'}` : `${p.after}${p.majorUpgrade ? ' (major upgrade)' : ''}`;
        const reach = side === 'before' ? `${p.priority} · ${REACH[p.reachability]}${p.exploitDemonstrated ? ', exploit demonstrated' : ''}` : 'No known advisories';
        for (const text of [p.name, version, reach]) {
          const td = document.createElement('td');
          td.textContent = text;
          row.append(td);
        }
        $('packages').append(row);
      }
      evidence();
    }

    $('before').onclick = () => { side = 'before'; render(); };
    $('after').onclick = () => { side = 'after'; render(); };
    $('evidence').onchange = evidence;
    render();
    $('app').hidden = false;
  } catch (e) {
    document.getElementById('load-error').hidden = false;
  }
})();
