const gsap=window.gsap;
const ScrollTrigger=window.ScrollTrigger;
const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const desktop=window.matchMedia('(min-width: 861px)').matches;
const finePointer=window.matchMedia('(pointer: fine)').matches;

const clamp=(min,max,value)=>Math.min(max,Math.max(min,value));
const q=(selector,root=document)=>root.querySelector(selector);
const qa=(selector,root=document)=>[...root.querySelectorAll(selector)];

if(gsap&&ScrollTrigger&&!reducedMotion){
  gsap.registerPlugin(ScrollTrigger);
  document.documentElement.classList.add('cinematic-ready');

  const statement=q('.statement');
  const mechanism=q('[data-mechanism]');
  const mechanismSticky=mechanism?.querySelector('.mechanism-sticky');
  const exploded=q('[data-exploded]');
  const sequence=q('[data-sequence]');
  const sequenceSticky=sequence?.querySelector('.sequence-sticky');
  const sequencePanels=qa('.sequence-panel');
  const anatomy=q('[data-anatomy]');
  const service=q('[data-service]');
  const development=q('[data-development]');
  const access=q('[data-access]');

  /* ---------------------------------------------------------------------
     GLOBAL PHYSICS
     Scroll velocity lightly distorts large type and moves the grain. This
     gives Lenis' inertial motion a visual consequence without turning the
     site into constant decorative animation.
  --------------------------------------------------------------------- */
  ScrollTrigger.create({
    trigger:document.documentElement,
    start:'top top',
    end:'bottom bottom',
    onUpdate:self=>{
      const velocity=clamp(-2500,2500,self.getVelocity());
      const skew=clamp(-2.25,2.25,velocity/1050);
      gsap.to('.hero-title,.mechanism-copy h2,.anatomy-copy h2,.service-copy h2',{
        skewX:skew,
        duration:.28,
        ease:'power3.out',
        overwrite:'auto'
      });
      gsap.to('.grain',{
        x:clamp(-5,5,velocity/520),
        y:clamp(-8,8,velocity/320),
        duration:.34,
        ease:'power2.out',
        overwrite:'auto'
      });
    }
  });

  /* ---------------------------------------------------------------------
     HERO DEPTH
     app.js owns the primary product animation. This layer moves surrounding
     planes so the hero reads as one spatial composition rather than a flat
     headline with an object in front of it.
  --------------------------------------------------------------------- */
  const hero=q('[data-hero]');
  const productStage=q('[data-product-stage]');
  if(hero&&productStage){
    gsap.set(productStage,{transformPerspective:1600,transformStyle:'preserve-3d'});
    const heroDepth=gsap.timeline({
      scrollTrigger:{trigger:hero,start:'top top',end:'bottom top',scrub:1.35,invalidateOnRefresh:true}
    });
    heroDepth
      .to('.hero-meta--left',{xPercent:-16,yPercent:-12,opacity:.35,ease:'none'},0)
      .to('.hero-meta--right',{xPercent:14,yPercent:-9,opacity:.28,ease:'none'},0)
      .to('.scroll-cue',{yPercent:30,opacity:0,ease:'none'},0)
      .to('.specimen-cross--h',{rotation:6,scaleX:1.12,ease:'none'},0)
      .to('.specimen-cross--v',{rotation:-5,scaleY:.88,ease:'none'},0)
      .to('.object-label--a',{xPercent:-24,yPercent:-16,ease:'none'},0)
      .to('.object-label--b',{xPercent:18,yPercent:10,ease:'none'},0)
      .to('.object-label--c',{xPercent:15,yPercent:22,ease:'none'},0);

    if(finePointer){
      const stageRX=gsap.quickTo(productStage,'rotationX',{duration:.9,ease:'power3.out'});
      const stageRY=gsap.quickTo(productStage,'rotationY',{duration:.9,ease:'power3.out'});
      const stageX=gsap.quickTo(productStage,'x',{duration:.95,ease:'power3.out'});
      const stageY=gsap.quickTo(productStage,'y',{duration:.95,ease:'power3.out'});
      window.addEventListener('pointermove',event=>{
        const nx=(event.clientX/window.innerWidth-.5)*2;
        const ny=(event.clientY/window.innerHeight-.5)*2;
        stageRX(-ny*2.8);
        stageRY(nx*4.6);
        stageX(nx*12);
        stageY(ny*8);
      },{passive:true});
    }
  }

  /* ---------------------------------------------------------------------
     STATEMENT -> MECHANISM
     The light editorial page collapses away while the dark mechanism plane
     opens toward the viewer. This is intentionally one continuous handoff.
  --------------------------------------------------------------------- */
  if(desktop&&statement&&mechanism&&mechanismSticky){
    gsap.set(mechanismSticky,{transformOrigin:'50% 50%',willChange:'transform,clip-path'});
    gsap.set(exploded,{transformPerspective:1700,transformStyle:'preserve-3d'});
    const handoff=gsap.timeline({
      scrollTrigger:{trigger:statement,start:'58% top',end:'bottom top',scrub:1.3,invalidateOnRefresh:true}
    });
    handoff
      .to('.statement-copy',{scale:.74,yPercent:-18,z:-110,rotationX:7,opacity:.16,filter:'blur(8px)',duration:1,ease:'power2.inOut'},0)
      .to('.statement-kicker',{opacity:0,y:-32,duration:.42,ease:'power2.in'},.06)
      .to('.statement-ghost',{scale:1.12,xPercent:-7,opacity:.02,duration:.8,ease:'none'},.02)
      .fromTo(mechanismSticky,
        {clipPath:'inset(10% 5% 10% 5% round 46px)',scale:.885,rotationX:3},
        {clipPath:'inset(0% 0% 0% 0% round 0px)',scale:1,rotationX:0,duration:1,ease:'power3.inOut'},
        .04
      )
      .fromTo(exploded,
        {z:-270,rotationX:9,rotationY:-11,scale:.79,opacity:.42},
        {z:0,rotationX:0,rotationY:0,scale:1,opacity:1,duration:.9,ease:'power3.out'},
        .14
      )
      .fromTo('.mechanism-copy',{x:-66,opacity:.32},{x:0,opacity:1,duration:.72,ease:'power3.out'},.2);
  }

  /* ---------------------------------------------------------------------
     MECHANISM CAMERA
     Individual layers are animated by app.js. Here the entire exploded object
     moves like a camera target, adding slow orbital depth without fighting the
     part transforms.
  --------------------------------------------------------------------- */
  if(desktop&&mechanism&&exploded){
    const camera=gsap.timeline({
      scrollTrigger:{trigger:mechanism,start:'top top',end:'bottom bottom',scrub:1.6,invalidateOnRefresh:true}
    });
    camera
      .fromTo(exploded,{rotationY:-3,rotationX:2,z:0},{rotationY:5,rotationX:-2,z:55,duration:.48,ease:'sine.inOut'},0)
      .to(exploded,{rotationY:-4,rotationX:1.5,z:-45,duration:.34,ease:'sine.inOut'},.48)
      .to(exploded,{rotationY:0,rotationX:0,z:0,duration:.18,ease:'power2.out'},.82)
      .to('.explode-grid',{rotation:2.2,scale:1.04,duration:1,ease:'none'},0)
      .to('.part-labels',{yPercent:-18,duration:1,ease:'none'},0);

    ScrollTrigger.create({
      trigger:mechanism,start:'top top',end:'bottom bottom',
      onUpdate:self=>{
        const phase=self.progress*5;
        qa('[data-focus]').forEach((item,index)=>{
          const proximity=Math.max(0,1-Math.abs(phase-(index+.5))/.75);
          gsap.to(item,{x:proximity*10,opacity:.46+proximity*.54,duration:.22,overwrite:'auto'});
        });
      }
    });
  }

  /* ---------------------------------------------------------------------
     MECHANISM -> HORIZONTAL FLOW
  --------------------------------------------------------------------- */
  if(desktop&&mechanismSticky&&sequence&&sequenceSticky){
    gsap.set(sequence,{backgroundColor:'#3a3835'});
    gsap.set(sequenceSticky,{transformOrigin:'50% 50%'});
    const toSequence=gsap.timeline({
      scrollTrigger:{trigger:sequence,start:'top bottom',end:'top top',scrub:1.18,invalidateOnRefresh:true}
    });
    toSequence
      .to(mechanismSticky,{scale:.925,clipPath:'inset(5% 3% 7% 3% round 36px)',rotationX:-3.5,duration:1,ease:'power2.inOut'},0)
      .to(exploded,{scale:.8,yPercent:-8,rotationZ:-2.4,z:-180,opacity:.44,duration:.84,ease:'power2.inOut'},.02)
      .to('.mechanism-copy',{y:-54,opacity:.18,duration:.66,ease:'power2.in'},.06)
      .fromTo(sequenceSticky,
        {clipPath:'inset(7% 4% 7% 4% round 38px)',scale:.935,rotationX:2},
        {clipPath:'inset(0% 0% 0% 0% round 0px)',scale:1,rotationX:0,duration:1,ease:'power3.inOut'},
        0
      )
      .to(sequence,{backgroundColor:'#edeae3',duration:.72,ease:'none'},.27)
      .fromTo('.sequence-head',{y:38,opacity:0},{y:0,opacity:1,duration:.54,ease:'power3.out'},.25);
  }

  /* ---------------------------------------------------------------------
     HORIZONTAL FLOW INTERNAL CHOREOGRAPHY
     app.js owns the horizontal translation. We derive a chapter index from the
     vertical progress and animate the internals without creating a second track
     tween, so there is no ScrollTrigger conflict.
  --------------------------------------------------------------------- */
  if(desktop&&sequence&&sequencePanels.length){
    let activePanel=-1;
    ScrollTrigger.create({
      trigger:sequence,
      start:'top top',
      end:'bottom bottom',
      onUpdate:self=>{
        const scaled=self.progress*(sequencePanels.length-1);
        const next=clamp(0,sequencePanels.length-1,Math.round(scaled));
        sequencePanels.forEach((panel,index)=>{
          const distance=index-scaled;
          const abs=Math.min(1,Math.abs(distance));
          const copy=q('.sequence-copy',panel);
          const orbit=q('.flow-orbit',panel);
          const word=q('.sequence-panel__word',panel);
          if(copy)gsap.set(copy,{x:distance*52,rotationY:distance*-5,opacity:1-abs*.6,transformPerspective:1000});
          if(orbit)gsap.set(orbit,{rotation:distance*18,scale:1-abs*.09,y:Math.sin(self.progress*Math.PI*2+index)*8});
          if(word)gsap.set(word,{xPercent:distance*-6,opacity:.035+(1-abs)*.045});
        });
        if(next!==activePanel){
          activePanel=next;
          sequencePanels.forEach((panel,index)=>panel.classList.toggle('is-current',index===next));
          const current=sequencePanels[next];
          if(current){
            gsap.fromTo(q('.sequence-copy h3',current),{y:22,opacity:.55},{y:0,opacity:1,duration:.48,ease:'power3.out',overwrite:true});
            gsap.fromTo(q('.sequence-number',current),{scale:.72,opacity:.2},{scale:1,opacity:1,duration:.42,ease:'back.out(1.7)',overwrite:true});
          }
        }
      }
    });
  }

  /* ---------------------------------------------------------------------
     FLOW -> INTERFACE
  --------------------------------------------------------------------- */
  if(desktop&&sequence&&sequenceSticky&&anatomy){
    const toAnatomy=gsap.timeline({
      scrollTrigger:{trigger:anatomy,start:'top bottom',end:'top top',scrub:1.08,invalidateOnRefresh:true}
    });
    toAnatomy
      .to(sequenceSticky,{clipPath:'inset(4% 2.5% 6% 2.5% round 32px)',scale:.95,rotationX:-2.4,duration:1,ease:'power2.inOut'},0)
      .fromTo(anatomy,
        {clipPath:'inset(12% 6% 12% 6% round 48px)',scale:.92},
        {clipPath:'inset(0% 0% 0% 0% round 0px)',scale:1,duration:1,ease:'power3.inOut'},
        0
      )
      .fromTo('.anatomy-copy',{x:-78,opacity:.18},{x:0,opacity:1,duration:.72,ease:'power3.out'},.2)
      .fromTo('.anatomy-visual',{x:92,z:-160,rotationY:-8,scale:.86,opacity:.28},{x:0,z:0,rotationY:0,scale:1,opacity:1,duration:.82,ease:'power3.out'},.14);
  }

  if(anatomy){
    gsap.set('.anatomy-visual',{transformPerspective:1500,transformStyle:'preserve-3d'});
    const anatomyInspect=gsap.timeline({
      scrollTrigger:{trigger:anatomy,start:'top top',end:'bottom top',scrub:1.4,invalidateOnRefresh:true}
    });
    anatomyInspect
      .to('.anatomy-visual',{rotationY:7,rotationX:-2.5,z:55,xPercent:2,duration:.5,ease:'sine.inOut'},0)
      .to('.anatomy-visual',{rotationY:-5,rotationX:2,z:-25,xPercent:-1,duration:.5,ease:'sine.inOut'},.5)
      .to('.anatomy-callout--one',{xPercent:-16,yPercent:-22,duration:1,ease:'none'},0)
      .to('.anatomy-callout--two',{xPercent:13,yPercent:16,duration:1,ease:'none'},0)
      .to('.anatomy-callout--three',{xPercent:-8,yPercent:20,duration:1,ease:'none'},0);
  }

  /* ---------------------------------------------------------------------
     INTERFACE -> SERVICE / SERVICE INSPECTION
  --------------------------------------------------------------------- */
  if(desktop&&anatomy&&service){
    const toService=gsap.timeline({
      scrollTrigger:{trigger:service,start:'top bottom',end:'top top',scrub:1.14,invalidateOnRefresh:true}
    });
    toService
      .to(anatomy,{clipPath:'inset(5% 3% 5% 3% round 34px)',scale:.948,duration:1,ease:'power2.inOut'},0)
      .to('.anatomy-visual',{rotationY:13,scale:.82,opacity:.34,z:-120,duration:.82,ease:'power2.inOut'},.03)
      .fromTo(service,
        {clipPath:'inset(8% 4% 8% 4% round 40px)',scale:.93},
        {clipPath:'inset(0% 0% 0% 0% round 0px)',scale:1,duration:1,ease:'power3.inOut'},
        0
      )
      .fromTo('.service-object',{rotationY:-14,x:78,z:-130,opacity:.28},{rotationY:0,x:0,z:0,opacity:1,duration:.78,ease:'power3.out'},.17)
      .fromTo('.service-copy',{x:-52,opacity:.4},{x:0,opacity:1,duration:.62,ease:'power3.out'},.24);
  }

  if(service){
    gsap.set('.service-object',{transformPerspective:1500,transformStyle:'preserve-3d'});
    gsap.to('.service-object',{rotationY:5,rotationX:-2,z:45,ease:'none',scrollTrigger:{trigger:service,start:'top top',end:'bottom top',scrub:1.45}});
    gsap.to('.service-word',{xPercent:-8,yPercent:-9,ease:'none',scrollTrigger:{trigger:service,start:'top bottom',end:'bottom top',scrub:1.6}});
  }

  /* ---------------------------------------------------------------------
     EVIDENCE / ACCESS EDITORIAL DECELERATION
     After the high-motion product chapters, the experience deliberately slows.
  --------------------------------------------------------------------- */
  if(development){
    qa('.development-row',development).forEach((row,index)=>{
      gsap.fromTo(row,{y:48,opacity:.28},{y:0,opacity:1,ease:'none',scrollTrigger:{trigger:row,start:'top 92%',end:'top 57%',scrub:.62}});
      const number=q('.development-row__number',row);
      if(number)gsap.fromTo(number,{rotationX:-68,y:24},{rotationX:0,y:0,transformPerspective:800,ease:'none',scrollTrigger:{trigger:row,start:'top 88%',end:'top 58%',scrub:.7}});
      const heading=q('h3',row);
      if(heading)gsap.fromTo(heading,{x:index%2?26:-26},{x:0,ease:'none',scrollTrigger:{trigger:row,start:'top 88%',end:'top 55%',scrub:.66}});
    });
  }

  if(access){
    gsap.fromTo('.access-copy',{y:82,opacity:.18,rotationX:-24},{y:0,opacity:1,rotationX:0,transformPerspective:1000,ease:'none',scrollTrigger:{trigger:access,start:'top 84%',end:'center 52%',scrub:.82}});
    gsap.to('.access-word',{xPercent:-6,rotationZ:2.5,ease:'none',scrollTrigger:{trigger:access,start:'top bottom',end:'bottom top',scrub:1.6}});
  }

  /* ---------------------------------------------------------------------
     SMALL PARALLAX / TYPOGRAPHIC DETAILS
  --------------------------------------------------------------------- */
  const parallax=(selector,fromY,toY,start='top bottom',end='bottom top',scrub=1.35)=>{
    const node=q(selector);
    if(!node)return;
    gsap.fromTo(node,{yPercent:fromY},{yPercent:toY,ease:'none',scrollTrigger:{trigger:node.closest('section')||node,start,end,scrub}});
  };
  parallax('.statement-kicker',18,-12);
  parallax('.access-copy',10,-8,'top bottom','bottom 20%',1.5);

  if(desktop){
    qa('.section-meta,.eyebrow,.sequence-head').forEach((accent,index)=>{
      const section=accent.closest('section');
      if(!section)return;
      gsap.fromTo(accent,
        {letterSpacing:'.23em',x:index%2?-18:18,opacity:.38},
        {letterSpacing:'.16em',x:0,opacity:1,ease:'none',scrollTrigger:{trigger:section,start:'top 90%',end:'top 38%',scrub:.7}}
      );
    });
  }

  const refresh=()=>ScrollTrigger.refresh();
  if(document.readyState==='complete')refresh();
  else window.addEventListener('load',refresh,{once:true});
  document.fonts?.ready?.then(refresh);
  window.setTimeout(refresh,220);
}

/* Product render runtime. The site still remains usable if it fails. */
import('/visuals.js').catch(()=>document.documentElement.classList.add('motion-static'));