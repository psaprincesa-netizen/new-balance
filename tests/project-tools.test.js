import test from 'node:test';
import assert from 'node:assert/strict';
import {dependencyError} from '../web/project-tools.js';
import {chartSvg,chartData} from '../web/chart.js';
test('dependencies reject cycles, missing tasks and premature work',()=>{const a={id:'a',status:'A fazer'},b={id:'b',status:'A fazer',dependsOn:['a']};assert.equal(dependencyError([a,b]),'');b.status='Em andamento';assert.match(dependencyError([a,b]),/Conclua/);a.status='Concluído';assert.equal(dependencyError([a,b]),'');a.dependsOn=['b'];assert.ok(dependencyError([a,b]));assert.ok(dependencyError([{id:'a',status:'A fazer',dependsOn:['missing']}]));});
test('advanced charts produce finite geometry and validate their inputs',()=>{for(const type of ['area','doughnut','horizontal','scatter','radar']){const svg=chartSvg([['X','Y'],[1,10],[2,0],[3,30]],{title:'<Unsafe>',type});assert.ok(svg.startsWith('<svg'));assert.ok(!svg.includes('NaN'));assert.ok(!svg.includes('<Unsafe>'));}assert.throws(()=>chartData([['X','Y'],['a',1]],'scatter'));assert.throws(()=>chartData([['X','Y'],[1,1],[2,2]],'radar'));});
