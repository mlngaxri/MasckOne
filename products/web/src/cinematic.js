const gsap=window.gsap;
const ScrollTrigger=window.ScrollTrigger;
const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const desktop=window.matchMedia('(min-width: 861px)').matches;

if(gsap&&ScrollTrigger&&!reducedMotion){
  gsap.registerPlugin(ScrollTrigger);

  const statement=document.querySelector('.statement');
  const mechanism=document.querySelector('[data-mechanism]');
  const mechanismSticky=mechanism?.querySelector('.mechanism-sticky');
  const sequence=document.querySelector('[data-sequence]');
  const sequenceSticky=sequence?.querySelector('.sequence-sticky');
  const anatomy=document.querySelector('[data-anatomy]');
  const service=document.querySelector('[data-service]');

  if(desktop&&statement&&mechanism&&mechanismSticky){
    gsap.set(mechanismSticky,{transformOrigin:'50% 50%',willChange:'transform,clip-path'});
    const handoffOut=gsap.timeline({scrollTrigger:{trigger:statement,start:'62% top',end:'bottom top',scrub:1.35,invalidateOnRefresh:true}});
    handoffOut
      .to('.statement-copy',{scale:.78,yPercent:-16,opacity:.22,filter:'blur(7px)',duration:1,ease:'power2.inOut'},0)
      .to('.statement-kicker',{opacity:0,y:-28,duration:.5},.12)
      .fromTo(mechanismSticky,{clipPath:'inset(8% 5% 8% 5% round 42px)',scale:.9},{clipPath:'inset(0% 0% 0% 0% round 0px)',scale:1,duration:1,ease:'power3.inOut'},.06)
      .fromTo('[data-exploded]',{z:-220,rotationX:8,rotationY:-9,scale:.82},{z:0,rotationX:0,rotationY:0,scale:1,duration:.88,ease:'power3.out'},.18);
  }

  if(desktop&&mechanism&&mechanismSticky&&sequence&&sequenceSticky){
    gsap.set(sequence,{backgroundColor:'#3a3835'});
    gsap.set(sequenceSticky,{transformOrigin:'50% 50%',clipPath:'inset(5% 3% 5% 3% round 32px)',scale:.95});
    const handoffIn=gsap.timeline({scrollTrigger:{trigger:sequence,start:'top bottom',end:'top top',scrub:1.2,invalidateOnRefresh:true}});
    handoffIn
      .to(mechanismSticky,{scale:.93,clipPath:'inset(5% 3% 7% 3% round 34px)',rotationX:-3,duration:1,ease:'power2.inOut'},0)
      .to('[data-exploded]',{scale:.84,yPercent:-6,rotationZ:-2,z:-150,duration:.82,ease:'power2.inOut'},.05)
      .to('.mechanism-copy',{y:-48,opacity:.26,duration:.7},.08)
      .to(sequenceSticky,{clipPath:'inset(0% 0% 0% 0% round 0px)',scale:1,duration:1,ease:'power3.inOut'},0)
      .to(sequence,{backgroundColor:'#edeae3',duration:.72,ease:'none'},.28)
      .fromTo('.sequence-head',{y:34,opacity:0},{y:0,opacity:1,duration:.56,ease:'power3.out'},.25);
  }

  if(desktop&&sequence&&anatomy){
    const sequenceToAnatomy=gsap.timeline({scrollTrigger:{trigger:anatomy,start:'top bottom',end:'top top',scrub:1.1,invalidateOnRefresh:true}});
    sequenceToAnatomy
      .to(sequenceSticky,{clipPath:'inset(4% 2% 5% 2% round 30px)',scale:.955,rotationX:-2,duration:1,ease:'power2.inOut'},0)
      .fromTo(anatomy,{clipPath:'inset(12% 7% 12% 7% round 48px)',scale:.93},{clipPath:'inset(0% 0% 0% 0% round 0px)',scale:1,duration:1,ease:'power3.inOut'},0)
      .fromTo('.anatomy-copy',{x:-70,opacity:.22},{x:0,opacity:1,duration:.7,ease:'power3.out'},.24)
      .fromTo('.anatomy-visual',{x:80,scale:.9,opacity:.35},{x:0,scale:1,opacity:1,duration:.78,ease:'power3.out'},.18);
  }

  if(desktop&&anatomy&&service){
    const anatomyToService=gsap.timeline({scrollTrigger:{trigger:service,start:'top bottom',end:'top top',scrub:1.15,invalidateOnRefresh:true}});
    anatomyToService
      .to(anatomy,{clipPath:'inset(5% 3% 5% 3% round 34px)',scale:.95,duration:1,ease:'power2.inOut'},0)
      .to('.face-field',{rotationY:12,scale:.84,opacity:.42,duration:.82,ease:'power2.inOut'},.05)
      .fromTo(service,{clipPath:'inset(7% 4% 8% 4% round 38px)',scale:.94},{clipPath:'inset(0% 0% 0% 0% round 0px)',scale:1,duration:1,ease:'power3.inOut'},0)
      .fromTo('.service-object',{rotationY:-12,x:70,opacity:.35},{rotationY:0,x:0,opacity:1,duration:.75,ease:'power3.out'},.18);
  }

  const parallax=(selector,fromY,toY,start='top bottom',end='bottom top',scrub=1.35)=>{
    const node=document.querySelector(selector);
    if(!node)return;
    gsap.fromTo(node,{yPercent:fromY},{yPercent:toY,ease:'none',scrollTrigger:{trigger:node.closest('section')||node,start,end,scrub}});
  };

  parallax('.object-label--a',14,-18,'top top','bottom top',1.45);
  parallax('.object-label--c',-10,18,'top top','bottom top',1.6);
  parallax('.statement-kicker',18,-12);
  parallax('.anatomy-callout--one',18,-14);
  parallax('.anatomy-callout--two',-12,18);
  parallax('.anatomy-callout--three',16,-10);
  parallax('.access-copy',12,-10,'top bottom','bottom 20%',1.5);

  if(desktop){
    const accents=[...document.querySelectorAll('.section-meta,.eyebrow,.sequence-head')];
    accents.forEach((accent,index)=>{
      const section=accent.closest('section');
      if(!section)return;
      gsap.fromTo(accent,{letterSpacing:'.23em',x:index%2?-18:18,opacity:.4},{letterSpacing:'.16em',x:0,opacity:1,ease:'none',scrollTrigger:{trigger:section,start:'top 88%',end:'top 36%',scrub:.7}});
    });
  }

  const depthTargets=[
    ['.hero-product__rear',-4,4],
    ['.hero-product__insert',3,-4],
    ['.face-halo',-3,3],
    ['.service-cartridge',2.5,-2.5],
    ['.access-word',-4,4]
  ];
  depthTargets.forEach(([selector,startRotation,endRotation])=>{
    const element=document.querySelector(selector);
    if(!element)return;
    gsap.fromTo(element,{rotationZ:startRotation},{rotationZ:endRotation,ease:'none',scrollTrigger:{trigger:element.closest('section')||element,start:'top bottom',end:'bottom top',scrub:1.6}});
  });

  if(document.readyState==='complete')ScrollTrigger.refresh();
  else window.addEventListener('load',()=>ScrollTrigger.refresh(),{once:true});
}