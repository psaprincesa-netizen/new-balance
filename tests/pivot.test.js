import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {calculatePivot,pivotDetails,parsePivotRange,safeCsvRows} from '../web/pivot.js';
const fixtures=JSON.parse(readFileSync(new URL('./pivot-cases.json',import.meta.url)));
for(const c of fixtures)test('pivot '+c.name,()=>{const r=calculatePivot(c.source,c.config);assert.deepEqual([r.headers,...r.rows],c.expected);});
test('drill-down uses underlying records, including grand total and blanks',()=>{
 const c=fixtures[0],r=calculatePivot(c.source,c.config);
 assert.deepEqual(pivotDetails(c.source,r,0,0),[c.source[0],c.source[1],c.source[2]]);
 assert.deepEqual(pivotDetails(c.source,r,r.rowKeys.length,r.columnKeys.length),c.source);
});
test('bounds, bad headers, formula errors and overflow are explicit',()=>{
 assert.equal(parsePivotRange('AA1:AB3000').width,2);
 for(const r of ['C3:A1','A1:ZZ5000','A1:A100001','A1'])assert.throws(()=>parsePivotRange(r));
 const c={rowField:0,valueField:1,columnField:null,aggregate:'sum'};
 for(const rows of [[['A','A'],['x',1]],[['A','B'],['x','#DIV/0!']],[['A','B'],['x',1e308],['x',1e308]]])assert.throws(()=>calculatePivot(rows,c));
 assert.deepEqual(safeCsvRows([['=1+1',-10,'+x']]),[["'=1+1",-10,"'+x"]]);
});
