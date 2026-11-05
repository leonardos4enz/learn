/* Avatares de bloub sin Vue: dibuja un fotograma del motor (window.Bloub) como el gabarit de BloubBot.vue
   y anima todos los avatares de la página con un solo requestAnimationFrame.

   new BloubBot.Bot(el, { shape, size, state, expr })  → bot.set(state, expr) · bot.aim(x, y) · bot.release()
   BloubBot.onFrame(fn)                                 → fn(dt) en cada fotograma, antes de dibujar
   BloubBot.setRunning(bool)                            → enciende o apaga la órbita (los ganchos de onFrame)
   BloubBot.still(shape, size, state, expr)             → SVG de un solo fotograma (avatares fijos de una lista)

   Cada avatar se dibuja solo mientras está visible: el grokpet del sidebar y del chat se animan en cualquier vista,
   y los de la órbita no gastan nada fuera de la Flota (spec 003, H5).

   Varias animaciones de bloub son de una sola pasada (tienen minDuration: anillos, cometa, remolino, "!").
   Mientras el estado dura se repiten, con un respiro en idle entre pasada y pasada, para que se note que siguen. */
(() => {
  'use strict';
  const B = window.Bloub;
  const BASE_FACE = new Map(B.STATES.map((s) => [s.id, s.baseFace]));
  const ONE_SHOT = new Map(B.STATES.filter((s) => s.minDuration && s.id !== 'burst').map((s) => [s.id, s.minDuration]));
  const REST = 0.7;
  const GAP = 0.8;

  let ink = '#0a0a0c';
  let paper = '#ffffff';
  function readTheme() {
    const cs = getComputedStyle(document.documentElement);
    ink = cs.getPropertyValue('--ink').trim() || ink;
    paper = cs.getPropertyValue('--sheet').trim() || paper;
  }

  function dotEl(d) {
    const fill = d.color ?? (d.depth === undefined ? ink : B.mixHex(paper, ink, d.depth));
    return d.d
      ? `<path d="${d.d}" transform="translate(${d.x} ${d.y}) rotate(${d.rot ?? 0}) scale(${B.RAYON})" fill="${fill}" opacity="${d.opacity}"/>`
      : `<circle cx="${d.x}" cy="${d.y}" r="${d.r}" fill="${fill}" opacity="${d.opacity}"/>`;
  }

  // Los ojos son huecos en una máscara (no formas blancas encima): así se recortan solos contra la silhouette.
  function frameSVG(f, uid, size) {
    const V = B.DEMI_VIEWBOX;
    const W = V * 2;
    let s = `<svg width="${size}" height="${size}" viewBox="${-V} ${-V} ${W} ${W}" aria-hidden="true"><defs>`
      + `<mask id="m${uid}" maskUnits="userSpaceOnUse" x="${-V}" y="${-V}" width="${W}" height="${W}"><path d="${f.bodyPath}" fill="#fff"/>`;
    for (const e of f.eyes) s += `<path d="${e.d}" transform="${e.matrix}" opacity="${e.alpha}" fill="#000"/>`;
    if (f.notch) s += `<circle cx="${f.notch.x}" cy="${f.notch.y}" r="${f.notch.r}" fill="#000"/>`;
    s += '</mask>';
    for (const a of f.arcs) {
      const n = a.grad.stops.length - 1;
      s += `<linearGradient id="g${uid}${a.id}" gradientUnits="userSpaceOnUse" x1="${a.grad.x1}" y1="${a.grad.y1}" x2="${a.grad.x2}" y2="${a.grad.y2}">`
        + a.grad.stops.map((c, i) => `<stop offset="${i / n}" stop-color="${c}"/>`).join('') + '</linearGradient>';
    }
    s += '</defs><g fill="none" stroke-linecap="round">';
    for (const a of f.arcs) s += `<path d="${a.back}" stroke="url(#g${uid}${a.id})" stroke-width="${a.width}" opacity="${a.opacity}"/>`;
    s += '</g>';
    if (f.dotsBehind) s += f.dots.map(dotEl).join('');
    // Fondo opaco con la forma del cuerpo: sin él, un anillo que pasa por detrás se vería dentro de los ojos.
    s += `<g opacity="${f.bodyAlpha}"><path d="${f.bodyPath}" fill="${paper}"/><g mask="url(#m${uid})"><rect x="${-V}" y="${-V}" width="${W}" height="${W}" fill="${ink}"/></g></g>`;
    if (!f.dotsBehind) s += f.dots.map(dotEl).join('');
    if (f.notif) s += `<circle cx="${f.notif.x}" cy="${f.notif.y}" r="${f.notif.r}" fill="${B.NOTIF_BLUE}"/>`;
    s += '<g fill="none" stroke-linecap="round">';
    for (const a of f.arcs) s += `<path d="${a.front}" stroke="url(#g${uid}${a.id})" stroke-width="${a.width}" opacity="${a.opacity}"/>`;
    return `${s}</g></svg>`;
  }

  const REDUCE = matchMedia('(prefers-reduced-motion: reduce)');
  let clock = 0;
  const bots = new Set();
  const hooks = new Set();

  class Bot {
    constructor(el, { shape = null, size = 80, state = 'idle', expr = null } = {}) {
      this.el = el;
      this.size = size;
      this.uid = Math.random().toString(36).slice(2, 8);
      this.state = state;
      this.expr = expr;
      this.eng = new B.BotEngine(B.RAYON, state, shape ? B.SHAPE_BY_ID.get(shape)?.radii ?? null : null, B.EXPRESSION_BY_ID.get(expr) ?? null);
      this.looking = false;
      this.resting = false;
      this.loopAt = clock + (ONE_SHOT.get(state) ?? 0) + GAP;
      bots.add(this);
    }

    set(state, expr = null) {
      if (state !== this.state) {
        this.state = state;
        this.eng.setState(state, clock);
        this.resting = false;
        this.loopAt = clock + (ONE_SHOT.get(state) ?? 0) + GAP;
        if (!BASE_FACE.get(state)) this.release();
      }
      if (expr !== this.expr) {
        this.expr = expr;
        this.eng.setExpression(B.EXPRESSION_BY_ID.get(expr) ?? null, clock);
      }
    }

    // Mira hacia un punto de la página; solo en los estados con cara de reposo (en los demás la mirada ES la animación).
    aim(x, y) {
      if (!BASE_FACE.get(this.state)) return;
      const r = this.el.getBoundingClientRect();
      if (!r.width) return;
      const nx = Math.max(-1, Math.min(1, (x - (r.left + r.width / 2)) / (innerWidth / 2)));
      const ny = Math.max(-1, Math.min(1, (y - (r.top + r.height / 2)) / (innerHeight / 2)));
      this.eng.setLook({ yaw: nx * 16, pitch: -ny * 13, mix: 1, spin: 0, wander: 0 }, clock);
      this.looking = true;
    }

    release() {
      if (!this.looking) return;
      this.eng.setLook(null, clock, 0.6);
      this.looking = false;
    }

    pump() {
      const d = ONE_SHOT.get(this.state);
      if (!d || clock < this.loopAt) return;
      if (this.resting) {
        this.eng.setState(this.state, clock);
        this.loopAt = clock + d + GAP;
      } else {
        this.eng.setState('idle', clock);
        this.loopAt = clock + REST;
      }
      this.resting = !this.resting;
    }

    // Sin cajas de diseño = oculto (vista no activa, panel cerrado, sidebar colapsado en teléfono).
    visible() {
      if (!this.el.isConnected) { bots.delete(this); return false; }
      return this.el.getClientRects().length > 0;
    }

    draw() {
      // Con movimiento reducido, un fotograma solo cuando cambia algo (estado, expresión o tamaño), ya asentado.
      if (REDUCE.matches) {
        const k = `${this.state}|${this.expr}|${this.size}`;
        if (k === this.drawn) return;
        this.drawn = k;
        this.el.innerHTML = frameSVG(this.eng.sample(clock + 2), this.uid, this.size);
        return;
      }
      this.drawn = null;
      this.pump();
      this.el.innerHTML = frameSVG(this.eng.sample(clock), this.uid, this.size);
    }
  }

  let last = performance.now();
  let running = true; // la órbita: sus ganchos solo corren en la vista Flota
  function loop(t) {
    const dt = Math.min(0.1, (t - last) / 1000);
    last = t;
    clock += dt;
    if (running) for (const fn of hooks) fn(dt);
    for (const b of bots) if (b.visible()) b.draw();
    requestAnimationFrame(loop);
  }
  function setRunning(on) {
    running = !!on;
  }

  // Un fotograma fijo, ya asentado, por forma, tamaño, estado y expresión (p. ej. el avatar de una fila de actividad).
  const stills = new Map();
  function still(shape = null, size = 22, state = 'idle', expr = 'neutre') {
    const k = `${shape}|${size}|${state}|${expr}`;
    if (!stills.has(k)) {
      const eng = new B.BotEngine(B.RAYON, state, shape ? B.SHAPE_BY_ID.get(shape)?.radii ?? null : null, B.EXPRESSION_BY_ID.get(expr) ?? null);
      stills.set(k, frameSVG(eng.sample(1.5), `s${stills.size}`, size));
    }
    return stills.get(k);
  }

  readTheme();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', readTheme);
  requestAnimationFrame(loop);

  window.BloubBot = { Bot, still, frameSVG, onFrame: (fn) => hooks.add(fn), readTheme, setRunning, get running() { return running; } };
})();
