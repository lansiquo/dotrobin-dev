const pages=[['Overview','index.html','robin application security'],['Pull Request Reviewer','pr-reviewer.html','python semgrep github project'],['Blackpearl','blackpearl.html','linux cms php'],['Blue','blue.html','windows smb eternalblue'],['Butler','butler.html','windows jenkins services']];
const el=id=>document.getElementById(id), dialog=el('palette');
function results(){const q=el('search').value.toLowerCase().trim();el('results').replaceChildren();for(const [title,url,tags] of pages){if((title+' '+tags).toLowerCase().includes(q)){const b=document.createElement('button');b.textContent=title+' ↗';b.onclick=()=>{location.href=url};el('results').append(b)}}el('empty').hidden=el('results').children.length>0}
function openPalette(){el('search').value='';results();dialog.showModal();el('search').focus()}
el('open').onclick=openPalette;el('close').onclick=()=>dialog.close();el('search').oninput=results;
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();dialog.open?dialog.close():openPalette()}});
dialog.addEventListener('keydown',e=>{const buttons=[...el('results').querySelectorAll('button')];const i=buttons.indexOf(document.activeElement);if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();if(buttons.length)buttons[(i+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length].focus()}if(e.key==='Enter'&&document.activeElement===el('search')&&buttons.length){e.preventDefault();buttons[0].click()}});

// Return directly to the selected article after history navigation.
window.addEventListener('pageshow',()=>{document.querySelectorAll('.detail-switcher').forEach(menu=>{menu.open=false})});

for(const menu of document.querySelectorAll('.detail-switcher')){
 const trigger=menu.querySelector('summary');
 menu.addEventListener('keydown',event=>{if(event.key==='Escape'&&menu.open){event.preventDefault();menu.open=false;trigger.focus()}});
 menu.addEventListener('click',event=>{if(event.target.closest('a'))menu.open=false});
 document.addEventListener('click',event=>{if(menu.open&&!menu.contains(event.target))menu.open=false});
}
