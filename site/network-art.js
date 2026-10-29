(()=>{
'use strict';
const canvas=document.getElementById('network-canvas');if(!canvas)return;
const ctx=canvas.getContext('2d');if(!ctx)return;
const art=canvas.closest('.network-art'),stage=canvas.parentElement,pause=document.getElementById('network-pause'),replay=document.getElementById('network-replay'),motion=matchMedia('(prefers-reduced-motion: reduce)');
let reduced=motion.matches;
let width=0,height=0,dpr=1,raf=0,last=0,elapsed=0,visible=true,paused=false,disposed=false,pointer={x:0,y:0};const duration=14500;
const nodes=[],edges=[],path=[];
for(let layer=0;layer<3;layer++){const count=[18,12,6][layer],radius=[290,190,85][layer];for(let i=0;i<count;i++){const a=i/count*Math.PI*2+layer*.18;nodes.push({x:Math.cos(a)*radius,y:(layer-1)*62,z:Math.sin(a)*radius,layer,angle:a});}}
nodes.push({x:0,y:30,z:0,layer:3,angle:0});
for(let start=0,layer=0;layer<3;layer++){const count=[18,12,6][layer];for(let i=0;i<count;i++){edges.push([start+i,start+(i+1)%count]);if(layer<2){const next=start+count;edges.push([start+i,next+Math.floor(i/count*[12,6][layer])]);}}start+=count;}
for(let i=30;i<36;i++)edges.push([i,36]);path.push(10,11,25,33,36);
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x)),ease=x=>1-Math.pow(1-clamp(x),3);
function project(n,t){const yaw=-.35+Math.sin(t*.00012)*.07+pointer.x*.07,co=Math.cos(yaw),si=Math.sin(yaw),x=n.x*co-n.z*si,z=n.x*si+n.z*co,y=n.y;const depth=1+z/1500;const scale=Math.min(width/790,height/425);return{x:width/2+x*scale/depth,y:height*.49+(z*.44-y)*scale/depth,z,scale:scale/depth};}
function stroke(a,b,color,line=1){ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle=color;ctx.lineWidth=line;ctx.stroke();}
function ring(cx,cy,rx,ry,color,line=1){ctx.beginPath();ctx.ellipse(cx,cy,rx,ry,0,0,Math.PI*2);ctx.strokeStyle=color;ctx.lineWidth=line;ctx.stroke();}
function draw(t){ctx.clearRect(0,0,width,height);const scale=Math.min(width/790,height/425),assemble=ease(t/2800),reveal=clamp((t-2400)/3000),travel=clamp((t-5500)/5200),settle=clamp((t-11000)/3500);const points=nodes.map((n,i)=>{const p=project(n,t),a=ease((t-i*35)/1700);return{...p,x:width/2+(p.x-width/2)*a,y:height*.49+(p.y-height*.49)*a,alpha:a};});
// Depth grid and quiet orbital geometry.
ctx.save();ctx.globalAlpha=.22*assemble;for(let i=-4;i<=4;i++){stroke(project({x:i*75,y:-100,z:-340},t),project({x:i*75,y:-100,z:340},t),'#5b436e');stroke(project({x:-340,y:-100,z:i*75},t),project({x:340,y:-100,z:i*75},t),'#5b436e');}ctx.restore();
for(let l=0;l<3;l++){const radius=[290,190,85][l]*scale;ring(width/2,height*.49-(l-1)*62*scale,radius*assemble,radius*.44*assemble,`rgba(186,160,255,${.08+.05*assemble})`);}
for(const [a,b] of edges){const p=points[a],q=points[b];stroke(p,q,`rgba(156,124,195,${.08+Math.min(p.alpha,q.alpha)*.19})`,.7);}
// Expanding discovery wave, softened rather than flashing.
if(reveal>0&&reveal<1){const r=reveal*355*scale;const glow=ctx.createRadialGradient(width/2,height*.49,Math.max(0,r-35*scale),width/2,height*.49,Math.max(1,r));glow.addColorStop(0,'#baa0ff00');glow.addColorStop(.85,'#baa0ff16');glow.addColorStop(1,'#baa0ff00');ctx.save();ctx.scale(1,.55);ctx.fillStyle=glow;ctx.fillRect(0,0,width,height/ .55);ctx.restore();ring(width/2,height*.49,r,r*.5,`rgba(205,177,255,${Math.sin(reveal*Math.PI)*.6})`,1.4);}
// Deterministic drifting motes stay within the drawing; no live data.
for(let i=0;i<44;i++){const a=i*2.39996+t*.000035,r=(80+(i*47)%255)*scale;ctx.fillStyle=`rgba(186,160,255,${(.12+(i%4)*.04)*assemble})`;ctx.beginPath();ctx.arc(width/2+Math.cos(a)*r,height*.49+Math.sin(a)*r*.46-(i%3)*20*scale,.7+(i%3)*.35,0,Math.PI*2);ctx.fill();}
// A travelling signal leaves a warm, persistent route through the layers.
for(let j=0;j<path.length-1;j++){const a=points[path[j]],b=points[path[j+1]],f=clamp(travel*4-j);if(f<=0)continue;const q={x:a.x+(b.x-a.x)*f,y:a.y+(b.y-a.y)*f};ctx.save();ctx.shadowColor='#e3aa74';ctx.shadowBlur=12;stroke(a,q,'#e1ad7d',2.2);ctx.restore();if(f<1){for(let k=0;k<12;k++){const d=clamp(f-k*.012);ctx.fillStyle=`rgba(255,218,175,${(1-k/12)*.8})`;ctx.beginPath();ctx.arc(a.x+(b.x-a.x)*d,a.y+(b.y-a.y)*d,(3-k*.16)*scale,0,Math.PI*2);ctx.fill();}}}
const sorted=points.map((p,i)=>({...p,i})).sort((a,b)=>a.z-b.z);for(const p of sorted){const n=nodes[p.i],rank=path.indexOf(p.i),hot=rank>=0&&travel*4>=rank,found=reveal*355>=Math.hypot(n.x,n.z),radius=(n.layer===3?10:3+n.layer)*p.scale;ctx.save();ctx.globalAlpha=p.alpha;ctx.shadowColor=hot?'#e3aa74':'#baa0ff';ctx.shadowBlur=hot?18:found?9:0;ctx.fillStyle=hot?'#f3c395':found?'#cbb3f2':'#736086';ctx.beginPath();ctx.arc(p.x,p.y,Math.max(1.5,radius),0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;if(found)ring(p.x,p.y,radius+4*p.scale,radius+4*p.scale,hot?'#e3aa7466':'#baa0ff44');ctx.restore();}
const core=points[36];if(travel===1){for(let i=0;i<3;i++)ring(core.x,core.y,(16+i*9+settle*4)*scale,(16+i*9+settle*4)*scale,`rgba(236,186,137,${(.32-i*.08)*(1-settle*.35)})`,1);}
}
function runnable(){return !disposed&&!motion.matches&&!paused&&visible&&!document.hidden&&elapsed<duration;}
function tick(now){raf=0;if(reduced!==motion.matches){settings();return;}if(!runnable()){last=0;return;}if(last)elapsed=Math.min(duration,elapsed+Math.min(now-last,50));last=now;draw(elapsed);if(elapsed>=duration){pause.textContent='Finished';pause.disabled=true;last=0;}else raf=requestAnimationFrame(tick);}
function schedule(){if(reduced!==motion.matches){settings();return;}if(runnable()&&!raf)raf=requestAnimationFrame(tick);if(!runnable()){cancelAnimationFrame(raf);raf=0;last=0;}}
function resize(){const r=stage.getBoundingClientRect();width=r.width;height=r.height;dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);draw(motion.matches?duration:elapsed);}
function settings(){reduced=motion.matches;pause.disabled=motion.matches;replay.disabled=motion.matches;pause.textContent=motion.matches?'Static':paused?'Resume':'Pause';draw(motion.matches?duration:elapsed);schedule();}
pause.addEventListener('click',()=>{paused=!paused;pause.textContent=paused?'Resume':'Pause';schedule();});replay.addEventListener('click',()=>{elapsed=0;last=0;paused=false;pause.disabled=false;pause.textContent='Pause';schedule();});
stage.addEventListener('pointermove',e=>{if(motion.matches||paused)return;const r=stage.getBoundingClientRect();pointer.x=(e.clientX-r.left)/r.width-.5;});stage.addEventListener('pointerleave',()=>{pointer.x=0;});
const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;schedule();},{threshold:.05});observer.observe(art);const ro=new ResizeObserver(resize);ro.observe(stage);document.addEventListener('visibilitychange',schedule);motion.addEventListener('change',settings);window.addEventListener('pagehide',()=>{disposed=true;cancelAnimationFrame(raf);ro.disconnect();observer.disconnect();motion.removeEventListener('change',settings);document.removeEventListener('visibilitychange',schedule);},{once:true});
art.dataset.ready='';art.querySelector('.network-controls').hidden=false;resize();settings();
})();
