(()=>{
  const imgs={front:'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-inspection-front-3q-v17c.webp',rear:'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-inspection-rear-3q-v17c.webp',side:'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-inspection-side-rear-v17c.webp'};
  Object.values(imgs).forEach(src=>{const i=new Image();i.src=src});
  const progress=document.getElementById('progressBar'),header=document.getElementById('header');
  const onScroll=()=>{const max=document.documentElement.scrollHeight-innerHeight;progress.style.transform=`scaleX(${max>0?scrollY/max:0})`;header.classList.toggle('scrolled',scrollY>30)};
  addEventListener('scroll',onScroll,{passive:true});onScroll();

  const navBtns=[...document.querySelectorAll('.nav button')];
  navBtns.forEach(btn=>btn.addEventListener('click',()=>document.getElementById(btn.dataset.target)?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})));
  const navSections=[...document.querySelectorAll('[data-nav]')];
  const navObs=new IntersectionObserver(entries=>{const hit=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];if(!hit)return;const key=hit.target.dataset.nav;navBtns.forEach(b=>b.classList.toggle('active',b.dataset.target===key))},{threshold:[.2,.45,.7],rootMargin:'-20% 0px -35%'});navSections.forEach(s=>navObs.observe(s));

  const revealObs=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');revealObs.unobserve(e.target)}}),{threshold:.12,rootMargin:'0px 0px -8%'});document.querySelectorAll('.reveal').forEach(el=>revealObs.observe(el));

  const hero=document.querySelector('.hero'),product=document.getElementById('heroProduct');
  if(hero&&product&&matchMedia('(pointer:fine)').matches&&!matchMedia('(prefers-reduced-motion: reduce)').matches){hero.addEventListener('pointermove',e=>{const r=hero.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;product.style.transform=`translate3d(${x*13}px,${y*9}px,0) rotate(${x*2-1.2}deg)`});hero.addEventListener('pointerleave',()=>product.style.transform='translate3d(0,0,0) rotate(-1.2deg)')}

  const journeyImage=document.getElementById('journeyImage'),readout=document.getElementById('journeyReadout'),steps=[...document.querySelectorAll('.journey-step')];let currentJourney='front';
  const setJourney=step=>{steps.forEach(s=>s.classList.toggle('active',s===step));readout.textContent=`${step.dataset.step} / ${step.dataset.label}`;const view=step.dataset.view;if(view!==currentJourney){currentJourney=view;journeyImage.classList.add('swap');setTimeout(()=>{journeyImage.src=imgs[view];journeyImage.alt=`MASCK ONE ${view} inspection view`;journeyImage.onload=()=>journeyImage.classList.remove('swap')},150)}};
  const stepObs=new IntersectionObserver(entries=>{const hit=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];if(hit)setJourney(hit.target)},{threshold:[.28,.5,.72],rootMargin:'-20% 0px -30%'});steps.forEach(s=>{stepObs.observe(s);s.addEventListener('focus',()=>setJourney(s));s.addEventListener('mouseenter',()=>{if(matchMedia('(pointer:fine)').matches)setJourney(s)})});

  const viewTabs=[...document.querySelectorAll('.view-tab')],inspectionImage=document.getElementById('inspectionImage'),inspectionLabel=document.getElementById('inspectionLabel');
  const labels={front:'Front three-quarter / V17C',rear:'Rear three-quarter / V17C',side:'Side rear / V17C'};let currentInspection='front';
  const setInspection=view=>{if(view===currentInspection)return;currentInspection=view;viewTabs.forEach(b=>b.classList.toggle('active',b.dataset.view===view));inspectionImage.classList.add('swap');setTimeout(()=>{inspectionImage.src=imgs[view];inspectionImage.alt=`MASCK ONE ${view} inspection`;inspectionLabel.textContent=labels[view];inspectionImage.onload=()=>inspectionImage.classList.remove('swap')},140)};viewTabs.forEach(b=>b.addEventListener('click',()=>setInspection(b.dataset.view)));

  const nodes=[...document.querySelectorAll('.system-node')],flow=document.getElementById('flow');let nodeIndex=0,nodeTimer;
  const setNode=(node,manual=false)=>{nodes.forEach(n=>n.classList.toggle('active',n===node));flow.dataset.state=node.dataset.state;nodeIndex=nodes.indexOf(node);if(manual){clearInterval(nodeTimer);startNodes()}};
  const startNodes=()=>{nodeTimer=setInterval(()=>{nodeIndex=(nodeIndex+1)%nodes.length;setNode(nodes[nodeIndex])},2800)};nodes.forEach(n=>n.addEventListener('click',()=>setNode(n,true)));startNodes();
})();
