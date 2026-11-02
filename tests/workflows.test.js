import test from 'node:test';
import assert from 'node:assert/strict';
import {responseTable,recordsWorkbook,answerError,safeCsv,scoreResponse,answerIsCorrect} from '../web/workflows.js';
test('duplicate and renamed questions retain each answer without column collisions',()=>{
 const r=responseTable({responses:[{at:1,questions:['Nome','Nome','Nome (2)','Data'],answers:['A','B','C','D']},{at:2,questions:['Nome','Outro'],answers:['E','F']}]});
 assert.equal(new Set(r.columns).size,r.columns.length);assert.deepEqual(r.rows[0].slice(1,5),['A','B','C','D']);assert.equal(r.rows[1].at(-1),'F');
});
test('200 record conversion includes header and keeps text formulas literal',()=>{
 const w=recordsWorkbook(['Texto','Número'],Array.from({length:200},(_,i)=>[i===0?'=1+1':'Registro '+i,String(i)]),['text','number']);
 assert.equal(w.sheets.records.cellData[200][1].v,199);assert.deepEqual(w.sheets.records.cellData[1][0],{v:'=1+1',t:1});
 assert.throws(()=>recordsWorkbook(Array(100).fill('X'),Array.from({length:1000},()=>Array(100).fill('Y'))));
});
test('answer validation catches stale required fields and invalid calendar dates',()=>{
 for(const [v,f] of [[' ',{type:'text',required:true}],['2026-02-30',{type:'date'}],['2026-99-99',{type:'date'}],['x',{type:'number'}],['missing',{type:'choice',options:['a']}],['a@x',{type:'email'}]])assert.ok(answerError(v,f));
 assert.equal(answerError('',{type:'text',required:false}),'');assert.equal(answerError('2028-02-29',{type:'date'}),'');assert.equal(safeCsv([['=1+1']])[0][0],"'=1+1");
});
test('quiz scoring matches the server rules',()=>{
  const fields=[{type:'choice',options:['A','B'],correct:'A',points:2},{type:'multiple',options:['1','2','3'],correct:['1','3']},{type:'number',correct:'10'},{type:'text',correct:'São Paulo'},{type:'scale',max:5}];
  assert.deepEqual(scoreResponse(fields,['A','3; 1','10.0',' SAO paulo ','4']),{score:5,total:5});
  assert.deepEqual(scoreResponse(fields,['B','1','','x','']),{score:0,total:5});
  assert.equal(answerIsCorrect('',{type:'text',correct:'a'}),false);
});
test('multiple selection and scale answers are validated',()=>{
  assert.equal(answerError('A; B',{type:'multiple',options:['A','B'],required:true}),'');
  assert.notEqual(answerError('A; C',{type:'multiple',options:['A','B']}),'');
  assert.notEqual(answerError('A; A',{type:'multiple',options:['A','B']}),'');
  assert.equal(answerError('7',{type:'scale',max:7}),'');
  assert.notEqual(answerError('8',{type:'scale',max:7}),'');
  assert.notEqual(answerError('',{type:'multiple',options:['A'],required:true}),'');
});
test('graded responses add a Nota column',()=>{
  const r=responseTable({questions:['Q'],responses:[{at:1,questions:['Q'],answers:['A'],score:1,total:2}]});
  assert.deepEqual(r.columns,['Data','Nota','Q']);
  assert.equal(r.rows[0][1],'1 / 2');
});
