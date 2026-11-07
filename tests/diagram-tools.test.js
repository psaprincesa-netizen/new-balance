import test from 'node:test';
import assert from 'node:assert/strict';
import {diagramTemplate,edgeGeometry,nodeShape} from '../web/diagram-tools.js';
test('templates are independent and have valid nodes, shapes and connectors',()=>{
 for(const name of ['flow','organization','network']){
  const a=diagramTemplate(name),b=diagramTemplate(name);
  a.content.nodes[0]='Changed';assert.notEqual(b.content.nodes[0],'Changed');
  assert.equal(a.content.nodes.length,a.content.shapes.length);
  for(const edge of a.content.edges)assert.ok(edge.from<a.content.nodes.length&&edge.to<a.content.nodes.length);
 }
 assert.throws(()=>diagramTemplate('unknown'));
});
test('arrow endpoints meet shape boundaries rather than hidden centers',()=>{
 assert.deepEqual(edgeGeometry({x:0,y:0},{x:300,y:0}),{x1:160,y1:30,x2:300,y2:30,labelX:230,labelY:22});
 const diagonal=edgeGeometry({x:0,y:0},{x:300,y:300},'decision','terminator');
 assert.ok(diagonal.x1>80&&diagonal.x1<160);assert.ok(diagonal.x2<380);
 for(const value of Object.values(diagonal))assert.ok(Number.isFinite(value));
 assert.match(nodeShape('decision'),/polygon/);assert.match(nodeShape('database'),/path/);
});
