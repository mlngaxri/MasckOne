const gsap=window.gsap;
const ScrollTrigger=window.ScrollTrigger;
const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const desktop=window.matchMedia('(min-width: 861px)').matches;

if(gsap&&ScrollTrigger&&!reducedMotion){
  gsap.registerPlugin(ScrollTrigger);

  const mechanism=document.querySelector('[data-mechanism]');
  const mechanismSticky=mechanism?.querySelector('.mechanism-sticky');
  const sequence=document.querySelector('[data-sequence]');
  const sequenceSticky=sequence?.querySelector('.sequence-sticky');

  if(desktop&&mechanism&&mechanismSticky&&sequence&&sequenceSticky){
    gsap.set(mechanismSticky,{transformOrigin:'50% 50%',willChange:'transform,clip-path'});
    gsap.set(sequence,{backgroundColor:'#3a3835'});
    gsap.set(sequenceSticky,{transformOrigin:'50% 50%',clipPath:'inset(4% 2% 4% 2% round 34px)',scale:.96});

    const handoffOut=gsap.timeline({
      scrollTrigger:{trigger:mechanism,start:'72% top',end:'bottom top',scrub:1.35,invalidateOnRefresh:true}
    });
    handoffOut
      .to(mechanism,{backgroundColor:'#edeae3',duration:1,ease:'none'},0)
      .to(mechanismSticky,{scale:.94,clipPath:'inset(3% 1.6% 4% 1.6% round 36px)',duration:1,ease:'power2.inOut'},0)
      .to('.mechanism-heading',{y:-46,opacity:.38,duration:.8,ease:'power2.inOut'},.08)
      .to('[data-exploded]',{scale:.86,yPercent:-6,rotationZ:-1.8,duration:.9,ease:'power2.inOut'},.05)
      .to('.part-label',{opacity:.22,duration:.4,ease:'power1.inOut'},.58)
      .to('.mechanism-progress',{opacity:0,duration:.24},.72);

    const handoffIn=gsap.timeline({
      scrollTrigger:{trigger:sequence,start:'top bottom',end:'top top',scrub:1.25,invalidateOnRefresh:true}
    });
    handoffIn
      .to(sequenceSticky,{clipPath:'inset(0% 0% 0% 0% round 0px)',scale:1,duration:1,ease:'power3.inOut'},0)
      .to(sequence,{backgroundColor:'#edeae3',duration:.78,ease:'none'},.22)
      .fromTo('.sequence-intro',{y:54,opacity:.42},{y:0,opacity:1,duration:.72,ease:'power3.out'},.18);
  }

  const parallax=(selector,fromY,toY,start='top bottom',end='bottom top')=>{
    const node=document.querySelector(selector);
    if(!node)return;
    gsap.fromTo(node,{yPercent:fromY},{yPercent:toY,ease:'none',scrollTrigger:{trigger:node.closest('section')||node,start,end,scrub:1.25}});
  };

  parallax('.stage-caption',10,-14,'top top','bottom top');
  parallax('.statement .eyebrow',22,-18,'top bottom','bottom top');
  parallax('.anatomy-callout--one',14,-12);
  parallax('.anatomy-callout--two',-10,16);
  parallax('.anatomy-callout--three',18,-8);
  parallax('.access-copy',12,-10,'top bottom','bottom 20%');

  if(desktop){
    const sections=[...document.querySelectorAll('.statement,.mechanism,.sequence,.anatomy,.service,.development,.access')];
    sections.forEach((section,index)=>{
      const accent=section.querySelector('.eyebrow,.index');
      if(!accent)return;
      gsap.fromTo(accent,{letterSpacing:'.22em',x:index%2?-16:16},{letterSpacing:'.13em',x:0,ease:'none',scrollTrigger:{trigger:section,start:'top 90%',end:'top 38%',scrub:.7}});
    });
  }

  const depthTargets=[
    ['.hero-product__rear',-4,5],
    ['.hero-product__insert',3,-4],
    ['.service-cartridge',2.4,-2.4],
    ['.access-mark',-3,3]
  ];
  depthTargets.forEach(([selector,startRotation,endRotation])=>{
    const element=document.querySelector(selector);
    if(!element)return;
    gsap.fromTo(element,{rotationZ:startRotation},{rotationZ:endRotation,ease:'none',scrollTrigger:{trigger:element.closest('section')||element,start:'top bottom',end:'bottom top',scrub:1.6}});
  });

  window.addEventListener('load',()=>ScrollTrigger.refresh(),{once:true});
}
