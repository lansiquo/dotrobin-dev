// Homepage: the section picked in the menu comes first.
// #writeups puts Lab writeups above Projects; #projects (or no choice) restores the default.
(() => {
  'use strict';
  const projects = document.getElementById('projects');
  const writeups = document.getElementById('writeups');
  if (!projects || !writeups || projects.parentNode !== writeups.parentNode) return;
  const parent = projects.parentNode;
  const links = [...document.querySelectorAll('.site-nav a')].filter(a => /#(projects|writeups)$/.test(a.getAttribute('href')));
  const samePage = url => url.pathname.replace(/index\.html$/, '') === location.pathname.replace(/index\.html$/, '');

  function apply(scroll) {
    const chosen = location.hash === '#writeups' ? 'writeups' : location.hash === '#projects' ? 'projects' : '';
    const writeupsFirst = chosen === 'writeups';
    const writeupsIsFirst = Boolean(projects.compareDocumentPosition(writeups) & Node.DOCUMENT_POSITION_PRECEDING);
    if (writeupsFirst && !writeupsIsFirst) parent.insertBefore(writeups, projects);
    if (!writeupsFirst && writeupsIsFirst) parent.insertBefore(projects, writeups);
    for (const a of links) {
      if (chosen && a.getAttribute('href').endsWith('#' + chosen)) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    }
    if (scroll && chosen) document.getElementById(chosen).scrollIntoView({ block: 'start' });
  }

  // Menu links point at index.html#…; on the homepage itself, switch sections without reloading.
  for (const a of links) {
    a.addEventListener('click', event => {
      const url = new URL(a.href);
      if (!samePage(url)) return;
      event.preventDefault();
      if (location.hash === url.hash) apply(true);
      else history.pushState(null, '', url.hash), apply(true);
    });
  }
  addEventListener('popstate', () => apply(true));
  addEventListener('hashchange', () => apply(true));
  apply(Boolean(location.hash));
})();
