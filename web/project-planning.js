import {schedule, projectBudget, isoDay} from './project.js';

// Snapshot the effective schedule, so dependency adjustments are part of the baseline.
export function captureBaseline(tasks, capturedAt = new Date().toISOString()) {
  const plan = schedule(tasks);
  if (plan.cycle) throw new Error('Resolva o ciclo de dependências antes de registrar a linha de base.');
  const dated = new Map(plan.tasks.map(t => [t.id, t]));
  return {capturedAt, tasks: tasks.map(t => {
    const row = dated.get(t.id);
    return {id: t.id, title: t.title, start: row ? isoDay(row.es) : '', due: row ? isoDay(row.ef) : '',
      plannedHours: t.plannedHours ?? 0, hourlyRate: t.hourlyRate ?? 0, fixedCost: t.fixedCost ?? 0};
  })};
}

export function baselineComparison(tasks, baseline) {
  if (!baseline) return null;
  const original = new Map(baseline.tasks.map(t => [t.id, t]));
  const now = captureBaseline(tasks);
  const current = new Map(now.tasks.map(t => [t.id, t]));
  const before = projectBudget(baseline.tasks), after = projectBudget(tasks);
  const rows = [...new Set([...original.keys(), ...current.keys()])].map(id => {
    const a = original.get(id), b = current.get(id);
    const delayDays = a?.due && b?.due ? Math.round((Date.parse(b.due) - Date.parse(a.due)) / 86400000) : null;
    return {id, title: b?.title ?? a.title, state: !a ? 'Adicionada' : !b ? 'Removida' : 'Existente',
      beforeDue: a?.due || '', due: b?.due || '', delayDays,
      costDelta: projectBudget(b ? [b] : []).plannedCents - projectBudget(a ? [a] : []).plannedCents};
  });
  return {rows, plannedDelta: after.plannedCents - before.plannedCents,
    actualDelta: after.actualCents - before.plannedCents, hoursDelta: after.plannedHours - before.plannedHours};
}

// Sweep interval boundaries; cost is independent of the length of the project.
// Planned effort is distributed uniformly across calendar days in the effective schedule.
export function resourceCapacity(tasks, resources = []) {
  const plan = schedule(tasks), dated = new Map(plan.tasks.map(t => [t.id, t]));
  const profiles = new Map(resources.map(r => [r.name, r.dailyHours]));
  const groups = new Map(), unallocated = [];
  for (const t of tasks) {
    if (!(t.plannedHours > 0)) continue;
    const name = t.assignee?.trim(), span = dated.get(t.id);
    if (!name || !span) { unallocated.push(t.title); continue; }
    if (!groups.has(name)) groups.set(name, new Map());
    const events = groups.get(name), load = t.plannedHours / (span.ef - span.es + 1);
    events.set(span.es, (events.get(span.es) || 0) + load);
    events.set(span.ef + 1, (events.get(span.ef + 1) || 0) - load);
  }
  const rows = [];
  for (const [name, events] of groups) {
    const capacity = profiles.get(name) ?? 8, dates = [...events.keys()].sort((a,b) => a-b);
    let load = 0, peak = 0, overloadedDays = 0;
    const conflicts = [];
    for (let i=0; i<dates.length-1; i++) {
      load += events.get(dates[i]); peak = Math.max(peak, load);
      if (load > capacity + 1e-8) {
        overloadedDays += dates[i+1] - dates[i];
        conflicts.push({start: isoDay(dates[i]), end: isoDay(dates[i+1]-1), dailyHours: load});
      }
    }
    rows.push({name, capacity, peak, overloadedDays, conflicts});
  }
  return {rows, unallocated};
}
