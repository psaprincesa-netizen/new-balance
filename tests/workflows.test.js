import test from 'node:test';
import assert from 'node:assert/strict';
import {responseTable,recordsWorkbook,answerError,safeCsv} from '../web/workflows.js';
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
