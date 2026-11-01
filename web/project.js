// Project scheduling for board tasks: dependencies, timeline and critical path (CPM).
// Dates are ISO calendar days (YYYY-MM-DD); durations are inclusive day counts.
const DAY = 86400000;

export function dayNumber(iso) {
  if (typeof iso !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null;
  const t = Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
  return Number.isFinite(t) ? Math.round(t / DAY) : null;
}

export function isoDay(n) {
  return new Date(n * DAY).toISOString().slice(0, 10);
}

export function ensureTaskIds(tasks) {
  const used = new Set(tasks.map((t) => t.id).filter(Boolean));
  let next = 1;
  for (const t of tasks) {
    if (t.id) continue;
    while (used.has('t' + next)) next++;
    t.id = 't' + next;
    used.add(t.id);
  }
  for (const t of tasks) {
    t.depends = (Array.isArray(t.depends) ? t.depends : []).filter((id) => id !== t.id && used.has(id));
  }
  return tasks;
}

// Returns the ids of a dependency cycle, or null when the graph is acyclic.
export function findCycle(tasks) {
  const byId = new Map(tasks.map((t) => [t.id, t]));
  const state = new Map();
  const stack = [];
  const visit = (id) => {
    state.set(id, 1);
    stack.push(id);
    for (const dep of byId.get(id)?.depends || []) {
      if (!byId.has(dep)) continue;
      if (state.get(dep) === 1) return stack.slice(stack.indexOf(dep));
      if (!state.get(dep)) {
        const found = visit(dep);
        if (found) return found;
      }
    }
    stack.pop();
    state.set(id, 2);
    return null;
  };
  for (const t of tasks) if (!state.get(t.id)) {
    const found = visit(t.id);
    if (found) return found;
  }
  return null;
}

// Planned span of a task: [start, end] day numbers, or null when it has no dates.
export function taskSpan(t) {
  const end = dayNumber(t.due);
  const start = dayNumber(t.start) ?? end;
  if (start === null || end === null) return null;
  return t.milestone ? [end, end] : [Math.min(start, end), Math.max(start, end)];
}

// Critical path method over dated tasks. Each task keeps its planned duration;
// a task cannot start before its own planned start nor before its predecessors end.
export function schedule(tasks) {
  const dated = tasks.filter((t) => taskSpan(t));
  if (!dated.length) return {tasks: [], start: null, end: null, critical: [], conflicts: [], cycle: null};
  const cycle = findCycle(dated);
  if (cycle) return {tasks: [], start: null, end: null, critical: [], conflicts: [], cycle};
  const byId = new Map(dated.map((t) => [t.id, t]));
  const info = new Map();
  const order = [];
  const seen = new Set();
  const visit = (t) => {
    if (seen.has(t.id)) return;
    seen.add(t.id);
    for (const dep of t.depends || []) if (byId.has(dep)) visit(byId.get(dep));
    order.push(t);
  };
  dated.forEach(visit);
  const conflicts = [];
  for (const t of order) {
    const [start, end] = taskSpan(t);
    const duration = t.milestone ? 0 : end - start + 1;
    const predecessorsEnd = Math.max(-Infinity, ...(t.depends || []).filter((d) => byId.has(d)).map((d) => info.get(d).ef));
    const es = Math.max(start, Number.isFinite(predecessorsEnd) ? predecessorsEnd + (t.milestone ? 0 : 1) : start);
    if (es > start) conflicts.push(t.id);
    info.set(t.id, {es, ef: t.milestone ? es : es + duration - 1, duration});
  }
  const projectEnd = Math.max(...[...info.values()].map((i) => i.ef));
  const projectStart = Math.min(...[...info.values()].map((i) => i.es));
  const successors = new Map(dated.map((t) => [t.id, []]));
  for (const t of dated) for (const d of t.depends || []) if (byId.has(d)) successors.get(d).push(t.id);
  for (const t of [...order].reverse()) {
    const i = info.get(t.id);
    const next = successors.get(t.id).map((s) => info.get(s).ls - (byId.get(s).milestone ? 0 : 1));
    i.lf = next.length ? Math.min(...next) : projectEnd;
    i.ls = t.milestone ? i.lf : i.lf - i.duration + 1;
    i.slack = i.ls - i.es;
  }
  const rows = order.map((t) => ({id: t.id, title: t.title, milestone: !!t.milestone, ...info.get(t.id), critical: info.get(t.id).slack === 0}));
  return {tasks: rows, start: projectStart, end: projectEnd, critical: rows.filter((r) => r.critical).map((r) => r.id), conflicts, cycle: null};
}
