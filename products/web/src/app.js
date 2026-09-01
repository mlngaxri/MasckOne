(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const coarse = matchMedia('(pointer: coarse)').matches;

  let lenis = null;
  if (!reduced && window.Lenis) {
    try {
      lenis = new Lenis({
        lerp: 0.072,
        smoothWheel: true,
        wheelMultiplier: 0.92,
        touchMultiplier: 1.03,
        syncTouch: false
      });
      const raf = time => {
        lenis.raf(time);
        requestAnimationFrame(raf);
      };
      requestAnimationFrame(raf);
    } catch (_) {
      lenis = null;
    }
  }

  const chapters = $$('.chapter');
  const chapterIds = new Set(chapters.map(ch => ch.id));
  const navBtns = $$('[data-nav-target]').filter(el => chapterIds.has(el.dataset.navTarget));
  const drawer = $('.nav-drawer');
  const menuBtn = $('.menu-button');
  const stair = $('.stair-transition');
  const strips = $$('.stair-transition > i');
  const transitionMark = $('.transition-mark');
  let transitioning = false;
  let activeChapter = 'object';
  let ticking = false;

  function chapterFromHash() {
    const hash = location.hash.replace('#', '');
    if (chapterIds.has(hash)) return hash;
    if (hash === 'anatomy') return 'object';
    return 'object';
  }

  function updateNavState() {
    navBtns.forEach(btn => {
      const active = btn.dataset.navTarget === activeChapter;
      btn.classList.toggle('active', active);
      if (active) btn.setAttribute('aria-current', 'page');
      else btn.removeAttribute('aria-current');
    });
  }

  function activateChapter(id, historyMode = 'push') {
    if (!chapterIds.has(id)) return;
    activeChapter = id;
    chapters.forEach(ch => ch.classList.toggle('active', ch.id === id));
    updateNavState();
    if (historyMode === 'push' && location.hash !== `#${id}`) history.pushState({ chapter: id }, '', `#${id}`);
    if (historyMode === 'replace') history.replaceState({ chapter: id }, '', `#${id}`);
    schedule();
  }

  const initialChapter = chapterFromHash();
  activateChapter(initialChapter, location.hash ? 'none' : 'replace');

  function setDrawer(open) {
    drawer.classList.toggle('open', open);
    drawer.setAttribute('aria-hidden', String(!open));
    menuBtn.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('drawer-open', open);
  }

  menuBtn.addEventListener('click', () => setDrawer(!drawer.classList.contains('open')));
  addEventListener('keydown', e => {
    if (e.key === 'Escape') setDrawer(false);
  });

  async function coverWithStair() {
    stair.style.pointerEvents = 'auto';
    transitionMark.getAnimations().forEach(a => a.cancel());
    transitionMark.style.opacity = '0';
    transitionMark.style.transform = 'translateY(18px)';
    strips.map((el, i) => {
      el.getAnimations().forEach(a => a.cancel());
      return el.animate(
        [{ transform: 'translateY(-105%)' }, { transform: 'translateY(0%)' }],
        {
          duration: 500,
          delay: i * 40,
          easing: 'cubic-bezier(.22,.74,.12,1)',
          fill: 'forwards'
        }
      );
    });
    await new Promise(resolve => setTimeout(resolve, 805));
    transitionMark.animate(
      [
        { opacity: 0, transform: 'translateY(18px) scale(.985)' },
        { opacity: 1, transform: 'translateY(0) scale(1)' }
      ],
      { duration: 220, easing: 'cubic-bezier(.22,.74,.12,1)', fill: 'forwards' }
    );
    await new Promise(resolve => setTimeout(resolve, 225));
  }

  async function uncoverWithStair() {
    transitionMark.animate(
      [
        { opacity: 1, transform: 'translateY(0)' },
        { opacity: 0, transform: 'translateY(-15px)' }
      ],
      { duration: 150, easing: 'ease-in', fill: 'forwards' }
    );
    strips.map((el, i) => el.animate(
      [{ transform: 'translateY(0%)' }, { transform: 'translateY(-105%)' }],
      {
        duration: 580,
        delay: (strips.length - 1 - i) * 28,
        easing: 'cubic-bezier(.22,.74,.12,1)',
        fill: 'forwards'
      }
    ));
    await new Promise(resolve => setTimeout(resolve, 790));
    stair.style.pointerEvents = 'none';
  }

  function hardScrollTop() {
    if (lenis) lenis.scrollTo(0, { immediate: true });
    else scrollTo(0, 0);
  }

  async function playTransition(targetId, historyMode = 'push') {
    if (transitioning || !chapterIds.has(targetId)) return;
    setDrawer(false);

    if (targetId === activeChapter) {
      if (lenis) lenis.scrollTo(0, { duration: 0.9 });
      else scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
      return;
    }

    transitioning = true;
    if (lenis) lenis.stop();

    if (reduced) {
      activateChapter(targetId, historyMode);
      hardScrollTop();
      transitioning = false;
      if (lenis) lenis.start();
      return;
    }

    try {
      await coverWithStair();
      activateChapter(targetId, historyMode);
      hardScrollTop();

      // Give layout one frame while the viewport is fully covered.
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      if (targetId === 'object') playHeroEntrance();
      await new Promise(resolve => setTimeout(resolve, 70));
      await uncoverWithStair();
    } finally {
      // Never allow an interrupted WAAPI sequence to trap interaction.
      stair.style.pointerEvents = 'none';
      strips.forEach(el => { el.style.transform = 'translateY(-105%)'; });
      if (lenis) lenis.start();
      transitioning = false;
    }
  }

  $$('[data-nav-target]').forEach(el => el.addEventListener('click', e => {
    const id = el.dataset.navTarget;
    if (!id) return;
    e.preventDefault();

    if (id === 'anatomy') {
      if (activeChapter !== 'object') {
        playTransition('object').then(() => {
          const target = $('#anatomy');
          if (lenis) lenis.scrollTo(target, { duration: 1.15 });
          else target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth' });
        });
      } else {
        const target = $('#anatomy');
        if (lenis) lenis.scrollTo(target, { duration: 1.15 });
        else target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth' });
      }
      return;
    }

    if (chapterIds.has(id)) playTransition(id);
  }));

  addEventListener('popstate', () => {
    const target = chapterFromHash();
    if (target !== activeChapter) playTransition(target, 'none');
  });

  // Reveal engine remains independent of third-party animation libraries.
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) entry.target.classList.add('visible');
    });
  }, { threshold: 0.14, rootMargin: '0px 0px -7%' });
  $$('.reveal').forEach(el => observer.observe(el));

  // Refined cursor on precise pointers only.
  if (!coarse && !reduced) {
    const cursor = $('.cursor');
    const label = $('.cursor span');
    let tx = innerWidth / 2, ty = innerHeight / 2, x = tx, y = ty;
    let vx = 0, vy = 0;

    addEventListener('pointermove', e => {
      vx = e.clientX - tx;
      vy = e.clientY - ty;
      tx = e.clientX;
      ty = e.clientY;
      cursor.style.opacity = '1';
    }, { passive: true });

    $$('[data-cursor],a,button').forEach(el => {
      el.addEventListener('pointerenter', () => {
        cursor.classList.add('active');
        label.textContent = el.dataset.cursor || 'OPEN';
      });
      el.addEventListener('pointerleave', () => {
        cursor.classList.remove('active');
        label.textContent = 'VIEW';
      });
    });

    const cursorRaf = () => {
      x += (tx - x) * 0.18;
      y += (ty - y) * 0.18;
      const speed = Math.min(1, Math.hypot(vx, vy) / 42);
      const angle = Math.atan2(vy, vx) * 180 / Math.PI;
      const sx = 1 + speed * 0.16;
      const sy = 1 - speed * 0.08;
      cursor.style.transform = `translate3d(${x}px,${y}px,0) translate(-50%,-50%) rotate(${angle}deg) scale(${sx},${sy})`;
      label.style.transform = `rotate(${-angle}deg) scale(${1 / sx},${1 / sy})`;
      vx *= 0.86;
      vy *= 0.86;
      requestAnimationFrame(cursorRaf);
    };
    cursorRaf();
  }

  if (!coarse && !reduced) {
    $$('.magnetic').forEach(el => {
      el.addEventListener('pointermove', e => {
        const r = el.getBoundingClientRect();
        const dx = (e.clientX - (r.left + r.width / 2)) * 0.1;
        const dy = (e.clientY - (r.top + r.height / 2)) * 0.1;
        el.style.transform = `translate3d(${dx}px,${dy}px,0)`;
      });
      el.addEventListener('pointerleave', () => { el.style.transform = ''; });
    });
  }

  const hero = $('.hero');
  const mask = $('.hero-mask');
  if (!coarse && !reduced && hero && mask) {
    hero.addEventListener('pointermove', e => {
      if (activeChapter !== 'object') return;
      const r = hero.getBoundingClientRect();
      const nx = (e.clientX - r.left) / r.width - 0.5;
      const ny = (e.clientY - r.top) / r.height - 0.5;
      mask.style.transform = `translate3d(${nx * 15}px,${ny * 11}px,42px) rotateX(${-ny * 2.2}deg) rotateY(${nx * 3.2}deg) rotate(-1.5deg)`;
    });
    hero.addEventListener('pointerleave', () => {
      mask.style.transform = 'translate3d(0,0,0) rotate(-1.5deg)';
    });
  }

  const anatomy = $('.anatomy-panel');
  const layers = $$('.layer');
  const labels = $$('.explode-label');
  const meter = $('.explode-meter b');
  const flowPanel = $('.flow-panel');
  const flowSteps = $$('.flow-step');
  const pathProgress = $('.path-progress');
  const progressLine = $('.scroll-line i');

  const desktopOffsets = [
    [-315, -12, -7, 24],
    [-155, 12, -3.5, 14],
    [0, 28, 0, 4],
    [160, 7, 4.5, -8],
    [325, 180, 7, 28]
  ];
  const tabletOffsets = [
    [-205, -12, -6, 22],
    [-104, 10, -3, 12],
    [0, 24, 0, 4],
    [106, 8, 4, -8],
    [200, 155, 6, 24]
  ];
  const mobileOffsets = [
    [-52, -130, -4, 22],
    [-30, -65, -2, 12],
    [0, 0, 0, 4],
    [28, 68, 2, -8],
    [48, 164, 4, 24]
  ];

  function update() {
    const sy = scrollY;
    const vh = innerHeight;
    const docH = Math.max(1, document.documentElement.scrollHeight - vh);
    if (progressLine) progressLine.style.transform = `scaleY(${clamp(sy / docH)})`;

    // Subtle hero depth. Product stays transparent and the text bands keep independent z-planes.
    if (!reduced && activeChapter === 'object' && hero && mask) {
      const hr = hero.getBoundingClientRect();
      if (hr.bottom > 0 && hr.top < vh) {
        const p = clamp(-hr.top / vh);
        mask.style.marginTop = `${p * 16}px`;
      }
    }

    // Clean explosion. Images never change opacity, filter or source while scrolling.
    if (activeChapter === 'object' && anatomy && meter) {
      const r = anatomy.getBoundingClientRect();
      const total = Math.max(1, r.height - vh);
      const p = clamp((-r.top) / total);
      const eased = 1 - Math.pow(1 - p, 3);
      const offsets = innerWidth <= 760 ? mobileOffsets : (innerWidth <= 1100 ? tabletOffsets : desktopOffsets);

      layers.forEach((layer, i) => {
        const [x, y, rot, z] = offsets[i];
        const scale = 1 - i * 0.008 * eased;
        layer.style.transform = `translate3d(${x * eased}px,${y * eased}px,${z * eased}px) rotate(${rot * eased}deg) scale(${scale})`;
        layer.style.opacity = '1';
        layer.style.visibility = 'visible';
      });
      meter.style.transform = `scaleX(${eased})`;
      labels.forEach((label, i) => label.classList.toggle('show', p > (0.2 + i * 0.075)));
    }

    if (activeChapter === 'system' && flowPanel && pathProgress) {
      const r = flowPanel.getBoundingClientRect();
      const p = clamp((vh - r.top) / (r.height + vh * 0.3));
      pathProgress.style.strokeDashoffset = String(1 - p);
      const idx = Math.min(2, Math.max(0, Math.floor(p * 3.05)));
      flowSteps.forEach((step, i) => step.classList.toggle('active', i === idx));
    }

    updateNavState();
  }

  function schedule() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      update();
      ticking = false;
    });
  }
  addEventListener('scroll', schedule, { passive: true });
  addEventListener('resize', schedule, { passive: true });

  function playHeroEntrance() {
    if (reduced || !hero || !mask || activeChapter !== 'object') return;
    hero.getAnimations({ subtree: true }).forEach(anim => {
      if (anim.playState === 'running') anim.cancel();
    });

    const parts = [
      $('.hero-copy .kicker'),
      ...$$('.hero-copy h1 > *'),
      $('.hero-copy .lede'),
      mask
    ].filter(Boolean);

    parts.forEach((el, i) => {
      const isMask = el === mask;
      const anim = el.animate(
        [
          {
            opacity: 0,
            transform: isMask ? 'translate3d(0,28px,0) scale(.955) rotate(-1.5deg)' : 'translateY(34px)'
          },
          {
            opacity: 1,
            transform: isMask ? 'translate3d(0,0,0) scale(1) rotate(-1.5deg)' : 'translateY(0)'
          }
        ],
        {
          duration: 820 + i * 90,
          delay: 120 + i * 88,
          easing: 'cubic-bezier(.22,.74,.12,1)',
          fill: 'both'
        }
      );
      // Release the animation's transform after entrance so desktop pointer depth remains live.
      anim.finished.then(() => anim.cancel()).catch(() => {});
    });

    const bands = [
      ['.marquee-back-one', -170, 470],
      ['.marquee-back-two', 170, 560],
      ['.marquee-front', 210, 650]
    ];
    bands.forEach(([selector, x, delay]) => {
      const el = $(selector);
      if (!el) return;
      const anim = el.animate(
        [
          { opacity: 0, transform: `translate3d(${x}px,0,0)` },
          { opacity: 1, transform: 'translate3d(0,0,0)' }
        ],
        { duration: 950, delay, easing: 'cubic-bezier(.22,.74,.12,1)', fill: 'both' }
      );
      anim.finished.then(() => anim.cancel()).catch(() => {});
    });
  }

  update();
  if (activeChapter === 'object') playHeroEntrance();

  if (location.hash === '#anatomy') {
    requestAnimationFrame(() => {
      const target = $('#anatomy');
      if (target) {
        if (lenis) lenis.scrollTo(target, { immediate: true });
        else target.scrollIntoView({ behavior: 'auto' });
      }
    });
  }
})();
