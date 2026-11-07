import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareDocumentInsertion,literalMarkdown,safeName,assertContentCapacity} from '../web/insert-menu.js';
test('document insertion remaps images without touching source or destination',()=>{
  const source={text:'![Foto](drap-image:same)\nTexto same',images:[{id:'same',src:'data:image/png;base64,AA==',alt:'Foto',width:60}]};
  const target={text:'Original',images:[{id:'same',src:'original'}],attachments:[{id:'file'}]};
  const result=prepareDocumentInsertion(source,target,()=> 'new-id');
  assert.equal(result.text,'![Foto](drap-image:new-id)\nTexto same');assert.equal(result.images[0].id,'new-id');
  assert.equal(source.images[0].id,'same');assert.equal(target.text,'Original');assert.equal(target.images.length,1);
  assert.throws(()=>prepareDocumentInsertion(source,{text:'',images:Array(20).fill({})}),/20 imagens/);
});
test('insertion checks serialized limits including Unicode and attachment overhead',()=>{
  assert.throws(()=>assertContentCapacity({text:'á'.repeat(310000)}),/espaço/);
  assert.throws(()=>prepareDocumentInsertion({text:'a'.repeat(1000000)},{text:'b'.repeat(900000)}),/espaço/);
  assert.doesNotThrow(()=>assertContentCapacity({text:'Texto válido'}));
});
test('plain text formatting stays literal and attachment filenames remain safe',()=>{
  assert.equal(literalMarkdown('**literal** [link](https://x.test)'), '\\*\\*literal\\*\\* \\[link\\]\\(https://x\\.test\\)');
  assert.equal(safeName('../relatório\n.pdf'),'.._relatório_.pdf');assert.equal(safeName(''), 'Arquivo');
});
