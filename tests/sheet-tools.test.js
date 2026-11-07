import test from 'node:test';
import assert from 'node:assert/strict';
import {transformRows,rangeStatistics,parseDataRange} from '../web/sheet-tools.js';
test('cleanup preserves typed values, literal replacement and the original data',()=>{
  const rows=[['  Ana   Silva ',12,true],['$& A.a',0,false],['=SUM(A1:A2)',null,'']];
  assert.deepEqual(transformRows(rows,'trim')[0],['Ana Silva',12,true]);
  assert.equal(rows[0][0],'  Ana   Silva ');
  assert.equal(transformRows(rows,'replace',{search:'A.a',replacement:'$&',caseSensitive:false})[1][0],'$& $&');
  assert.equal(transformRows(rows,'trim')[2][0],'=SUM(A1:A2)');
});
test('unique, blank rows, split and transpose keep headers and rectangular shape',()=>{
  assert.deepEqual(transformRows([['Name'],['Name'],['ANA'],['ana'],['']], 'unique',{header:true,caseSensitive:false}),[['Name'],['Name'],['ANA'],['']]);
  assert.deepEqual(transformRows([['Header'],[''],[0],[false]],'empty',{header:true}),[['Header'],[0],[false]]);
  assert.deepEqual(transformRows([['A;B'],['C']], 'split',{separator:';'}),[['A','B'],['C','']]);
  assert.deepEqual(transformRows([[1,2],[3,4]],'transpose'),[[1,3],[2,4]]);
  assert.throws(()=>transformRows([[1,2]],'split'),/coluna/);
  assert.throws(()=>transformRows([['']], 'empty'),/não contém/);
  assert.throws(()=>transformRows([[1]],'replace'),/localizar/);
});
test('statistics use numbers without coercing text or booleans',()=>{
  assert.deepEqual(rangeStatistics([[2,'3',false,null],[4,'',-3,'x']]),{filled:6,numbers:3,sum:3,average:1,min:-3,max:4});
  assert.equal(rangeStatistics([['x']]).average,null);
});

test('range bounds allow single cells and reject oversized or reversed allocations',()=>{
  assert.equal(parseDataRange('A1').height,1);
  assert.equal(parseDataRange('AA1:AB3').width,2);
  for(const address of ['B2:A1','A1:Z100000','A0','XFE1','A1:XFD1000'])assert.throws(()=>parseDataRange(address));
});
