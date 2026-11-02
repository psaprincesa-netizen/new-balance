import test from 'node:test';
import assert from 'node:assert/strict';
import {schedule, findCycle, ensureTaskIds, dayNumber, isoDay} from '../web/project.js';

const T = (id, start, due, depends = [], extra = {}) => ({id, title: id, start, due, depends, status: 'A fazer', ...extra});

test('dates round-trip and invalid dates are rejected', () => {
  assert.equal(isoDay(dayNumber('2026-11-01')), '2026-11-01');
  assert.equal(dayNumber('01/11/2026'), null);
});

test('critical path follows the longest dependency chain', () => {
  const tasks = [
    T('a', '2026-01-01', '2026-01-03'),
    T('b', '2026-01-04', '2026-01-10', ['a']),
    T('c', '2026-01-04', '2026-01-05', ['a']),
    T('d', '2026-01-11', '2026-01-12', ['b', 'c']),
  ];
  const s = schedule(tasks);
  assert.deepEqual(s.critical, ['a', 'b', 'd']);
  assert.equal(isoDay(s.end), '2026-01-12');
  assert.equal(s.tasks.find((t) => t.id === 'c').slack, 5);
  assert.deepEqual(s.conflicts, []);
});

test('a task planned before its predecessor ends is reported and pushed', () => {
  const s = schedule([T('a', '2026-01-01', '2026-01-05'), T('b', '2026-01-03', '2026-01-04', ['a'])]);
  assert.deepEqual(s.conflicts, ['b']);
  assert.equal(isoDay(s.tasks.find((t) => t.id === 'b').es), '2026-01-06');
});

test('milestones have zero duration and stay on the path', () => {
  const s = schedule([T('a', '2026-01-01', '2026-01-02'), T('m', '', '2026-01-02', ['a'], {milestone: true}), T('b', '2026-01-03', '2026-01-04', ['m'])]);
  assert.deepEqual(s.critical, ['a', 'm', 'b']);
  assert.equal(s.tasks.find((t) => t.id === 'm').duration, 0);
});

test('cycles are detected and undated tasks are ignored', () => {
  assert.deepEqual(findCycle([T('a', '', '', ['b']), T('b', '', '', ['a'])]).sort(), ['a', 'b']);
  assert.ok(schedule([T('a', '2026-01-01', '2026-01-02', ['b']), T('b', '2026-01-01', '2026-01-02', ['a'])]).cycle);
  assert.equal(schedule([T('x', '', '')]).tasks.length, 0);
});

test('ids are assigned without collisions and dangling dependencies are dropped', () => {
  const tasks = ensureTaskIds([{title: 'a'}, {id: 't1', title: 'b', depends: ['t1', 'zz']}, {title: 'c', depends: ['t1']}]);
  assert.deepEqual(tasks.map((t) => t.id), ['t2', 't1', 't3']);
  assert.deepEqual(tasks[1].depends, []);
  assert.deepEqual(tasks[2].depends, ['t1']);
});
