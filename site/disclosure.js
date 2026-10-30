(()=>{'use strict';
const article=document.querySelector('.content.article');if(!article)return;
const entries=[];
for(const [i,heading] of [...article.children].filter(e=>e.tagName==='H2').entries()){
 if(heading.id==='environment')continue;
 const nodes=[];let next=heading.nextElementSibling;
 while(next&&next.tagName!=='H2'){if(next.matches('p')&&next.children.length===1&&next.firstElementChild.matches('a[href^="index.html"]'))break;nodes.push(next);next=next.nextElementSibling;}
 const prose=nodes.flatMap(n=>n.matches('p,li')?[n]:[...n.querySelectorAll('p,li')]).find(n=>n.textContent.trim());
 if(!prose||(!nodes.some(n=>n.matches('pre,figure,ol,ul,div'))&&nodes.map(n=>n.textContent).join(' ').length<280))continue;
 const section=document.createElement('section');section.className='reading-section';heading.before(section);section.append(heading);
 const preview=document.createElement('p');preview.className='section-preview';preview.textContent=prose.textContent.trim();section.append(preview);
 const body=document.createElement('div');body.className='section-full';body.id='reading-section-'+i;nodes.forEach(n=>body.append(n));section.append(body);
 const button=document.createElement('button');button.type='button';button.className='section-toggle';button.setAttribute('aria-controls',body.id);section.append(button);
 const entry={section,heading,preview,body,button,open:false};entries.push(entry);
 button.addEventListener('click',()=>set(entry,!entry.open));
 body.addEventListener('beforematch',()=>set(entry,true));
}
if(!entries.length)return;
function set(entry,open){entry.open=open;entry.preview.hidden=open;if(open)entry.body.removeAttribute('hidden');else entry.body.setAttribute('hidden','until-found');entry.button.setAttribute('aria-expanded',String(open));entry.button.textContent=open?'Show less':'Show more';entry.button.setAttribute('aria-label',(open?'Show less: ':'Show more: ')+entry.heading.textContent);}
const toolbar=document.createElement('div');toolbar.className='reading-controls';toolbar.setAttribute('role','group');toolbar.setAttribute('aria-label','Reading options');
for(const [label,open] of [['Expand all',true],['Collapse all',false]]){const button=document.createElement('button');button.type='button';button.textContent=label;button.addEventListener('click',()=>entries.forEach(e=>set(e,open)));toolbar.append(button);}
const hint=document.createElement('span');hint.textContent='Three-line previews · expand for commands and evidence';toolbar.append(hint);entries[0].section.before(toolbar);
entries.forEach(e=>set(e,false));
function revealHash(){let id;try{id=decodeURIComponent(location.hash.slice(1));}catch{return;}const target=document.getElementById(id);if(!target)return;const entry=entries.find(e=>e.section.contains(target));if(entry){set(entry,true);requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));}}
window.addEventListener('hashchange',revealHash);window.addEventListener('pageshow',revealHash);revealHash();
// Expand for browser Find in engines without hidden-until-found support.
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='f')entries.forEach(entry=>set(entry,true));});
let printState;window.addEventListener('beforeprint',()=>{printState=entries.map(e=>e.open);entries.forEach(e=>set(e,true));});window.addEventListener('afterprint',()=>{if(printState)entries.forEach((e,i)=>set(e,printState[i]));printState=null;});
})();
