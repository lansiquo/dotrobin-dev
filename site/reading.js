(()=>{'use strict';const menu=document.querySelector('.contents-menu');if(!menu)return;const media=matchMedia('(min-width:1201px)'),trigger=menu.querySelector('summary'),links=[...menu.querySelectorAll('a')],sections=links.map(a=>document.getElementById(decodeURIComponent(a.hash.slice(1)))).filter(Boolean);let queued=false;
function layout(){menu.open=media.matches;trigger.tabIndex=media.matches?-1:0;update();}
function update(){queued=false;let current=sections[0];for(const section of sections){if(section.getBoundingClientRect().top<=100)current=section;else break;}if(window.scrollY+innerHeight>=document.documentElement.scrollHeight-4)current=sections.at(-1);for(const a of links){if(current&&a.hash==='#'+current.id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');}}
function queue(){if(!queued){queued=true;requestAnimationFrame(update);}}
menu.addEventListener('click',e=>{const link=e.target.closest('a');if(link&&!media.matches){menu.open=false;const target=document.getElementById(decodeURIComponent(link.hash.slice(1)));if(target){target.tabIndex=-1;target.focus({preventScroll:true});}}});
menu.addEventListener('keydown',e=>{if(e.key==='Escape'&&!media.matches&&menu.open){menu.open=false;trigger.focus();}});
menu.addEventListener('toggle',()=>{if(media.matches&&!menu.open)menu.open=true;});
window.addEventListener('scroll',queue,{passive:true});window.addEventListener('resize',queue,{passive:true});window.addEventListener('hashchange',queue);window.addEventListener('pageshow',layout);media.addEventListener('change',layout);layout();})();
