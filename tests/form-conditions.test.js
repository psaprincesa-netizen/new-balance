import test from 'node:test';
import assert from 'node:assert/strict';
import {visibleQuestions,canonicalAnswers,cleanConditions} from '../web/form-conditions.js';
import {scoreResponse} from '../web/workflows.js';
const fields=[{type:'choice',options:['Sim','Não']},{type:'choice',options:['A','B'],correct:'A',points:5,showWhen:{question:0,value:'Sim'}},{type:'text',correct:'ok',points:10,showWhen:{question:1,value:'A'}}];
test('conditional chains hide descendants and erase hidden values',()=>{
 assert.deepEqual(visibleQuestions(fields,['Não','A','ok']),[true,false,false]);
 assert.deepEqual(canonicalAnswers(fields,['Não','A','ok']),['Não','','']);
 assert.deepEqual(visibleQuestions(fields,['Sim','A','ok']),[true,true,true]);
 assert.deepEqual(scoreResponse(fields,['Não','A','ok']),{score:0,total:0});
 assert.deepEqual(scoreResponse(fields,['Sim','A','ok']),{score:15,total:15});
});
test('question removal and option changes repair condition indices',()=>{
 const copy=structuredClone(fields);copy.splice(1,1);cleanConditions(copy,1);assert.equal(copy[1].showWhen,undefined);
 const changed=structuredClone(fields);changed[0].options=['Talvez'];cleanConditions(changed);assert.equal(changed[1].showWhen,undefined);
});
