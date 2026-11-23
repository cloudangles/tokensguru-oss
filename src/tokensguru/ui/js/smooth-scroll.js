const LINE_HEIGHT = 40;
const MIN_NOTCH = 30;
const TIME_CONSTANT = 85;
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const active = new Map();

function isNotchedWheel(event) {
  if (event.deltaX !== 0) return false;
  if (event.deltaMode === 1) return true;
  if (Math.abs(event.deltaY) < MIN_NOTCH) return false;
  const notch = event.wheelDeltaY;
  return notch === undefined ? event.deltaY % 100 === 0 : notch % 120 === 0;
}

function canScroll(element, direction) {
  const room = element.scrollHeight - element.clientHeight;
  return room > 1 && (direction < 0 ? element.scrollTop > 0 : element.scrollTop < room - 1);
}

function scroller(start, direction) {
  for (let node = start; node && node !== document.body; node = node.parentElement) {
    if (["TEXTAREA", "SELECT", "INPUT"].includes(node.tagName)) return null;
    if (/(auto|scroll)/.test(getComputedStyle(node).overflowY) && canScroll(node, direction)) return node;
  }
  const page = document.scrollingElement;
  return canScroll(page, direction) ? page : null;
}

function stop(element) {
  const state = active.get(element);
  if (state) cancelAnimationFrame(state.frame);
  active.delete(element);
}

function stopAll() {
  for (const element of [...active.keys()]) stop(element);
}

function step(element, state, now) {
  const elapsed = Math.min(now - state.time, 48);
  state.time = now;
  const distance = state.target - element.scrollTop;
  if (Math.abs(distance) <= 1) {
    element.scrollTo({ top: state.target, behavior: "instant" });
    active.delete(element);
    return;
  }
  const move = distance * (1 - Math.exp(-elapsed / TIME_CONSTANT));
  element.scrollTo({ top: element.scrollTop + (Math.abs(move) < 1 ? Math.sign(distance) : move), behavior: "instant" });
  state.frame = requestAnimationFrame((time) => step(element, state, time));
}

function onWheel(event) {
  if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  if (reducedMotion.matches || !isNotchedWheel(event)) return;
  const pixels = event.deltaY * (event.deltaMode === 1 ? LINE_HEIGHT : 1);
  const element = scroller(event.target, pixels);
  if (!element || !pixels) return;
  event.preventDefault();
  let state = active.get(element);
  const base = state ? state.target : element.scrollTop;
  const limit = element.scrollHeight - element.clientHeight;
  const target = Math.min(limit, Math.max(0, base + pixels));
  if (!state) {
    state = { target, time: performance.now(), frame: 0 };
    active.set(element, state);
    state.frame = requestAnimationFrame((time) => step(element, state, time));
  } else state.target = target;
}

export function enableSmoothScroll() {
  window.addEventListener("wheel", onWheel, { passive: false });
  for (const type of ["pointerdown", "keydown", "touchstart"]) window.addEventListener(type, stopAll, { passive: true });
}
