import test from 'node:test';
import assert from 'node:assert/strict';
import {captureBaseline,baselineComparison,resourceCapacity} from '../web/project-planning.js';
import {ensureTaskIds,dayNumber} from '../web/project.js';
const task=(id,extra={})=>({id,title:id,status:'A fazer',start:'2026-01-01',due:'2026-01-02',assignee:'Ana',plannedHours:16,hourlyRate:50,fixedCost:10,...extra});

test('baseline is independent of later edits, includes added and removed tasks and effective dependency dates',()=>{
 const tasks=[task('a'),task('b',{depends:['a']})];
 const base=captureBaseline(tasks,'2026-01-01T00:00:00Z');
 assert.equal(base.tasks[1].due,'2026-01-04');
 tasks[0].plannedHours=20;tasks[1].due='2026-01-03';
 let c=baselineComparison(tasks,base);assert.equal(c.plannedDelta,20000);assert.equal(c.rows[1].delayDays,1);
 assert.equal(base.tasks[0].plannedHours,16);
 c=baselineComparison([tasks[0],task('c')],base);
 assert.equal(c.rows.find(r=>r.id==='b').state,'Removida');
 assert.equal(c.rows.find(r=>r.id==='c').state,'Adicionada');
 assert.equal(c.rows.find(r=>r.id==='b').costDelta,-81000);
});

test('removed baseline ids are not reused and impossible dates do not normalize',()=>{
 const tasks=ensureTaskIds([{title:'nova'}],['t1']);assert.equal(tasks[0].id,'t2');
 assert.equal(dayNumber('2026-02-31'),null);assert.notEqual(dayNumber('2024-02-29'),null);
});

test('capacity sums overlap, honors zero capacity, and reports unallocated hours',()=>{
 const tasks=[task('a'),task('b',{start:'2026-01-02',due:'2026-01-03'}),task('c',{start:'',due:''}),task('d',{assignee:''})];
 const c=resourceCapacity(tasks);assert.equal(c.rows[0].peak,16);assert.equal(c.rows[0].overloadedDays,1);
 assert.deepEqual(c.rows[0].conflicts,[{start:'2026-01-02',end:'2026-01-02',dailyHours:16}]);
 assert.deepEqual(c.unallocated,['c','d']);assert.equal(resourceCapacity(tasks,[{name:'Ana',dailyHours:0}]).rows[0].overloadedDays,3);
 assert.equal(resourceCapacity([task('m',{start:'',due:'2026-01-01',milestone:true})]).rows[0].peak,16);
 assert.equal(resourceCapacity([task('a'),task('b',{depends:['a']})]).rows[0].overloadedDays,0);
});
