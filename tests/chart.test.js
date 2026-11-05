import test from 'node:test';
import assert from 'node:assert/strict';
import {chartData,chartSvg,CHART_TYPES} from '../web/chart.js';
test('charts use numeric cells, handle negative values and escape labels',()=>{
 const rows=[['Nome','Valor'],['<script>',-20],['B',30]];
 assert.equal(chartData(rows,'bar').series[0].values[1],30);
 const svg=chartSvg(rows,{type:'bar',title:'<script>'});assert.ok(svg.includes('&lt;script&gt;'));assert.ok(!svg.includes('<script>'));
 assert.throws(()=>chartData(rows,'pie'));
 assert.throws(()=>chartData([['Nome','Valor'],['A','#DIV/0!']],'line'));
 assert.ok(chartSvg([['Nome','Valor'],['A',20]],{type:'pie',title:'Parte'}).includes('<circle'));
});
test('every chart type renders several series where allowed',()=>{
 const rows=[['Mês','Receita','Custo','Lucro'],['Jan',10,4,6],['Fev',12,5,-1],['Mar',8,3,5]];
 for(const type of Object.keys(CHART_TYPES)){
  if(type==='pie'||type==='doughnut'){assert.throws(()=>chartData(rows,type),/duas colunas/);continue;}
  if(type==='scatter'){assert.throws(()=>chartData(rows,type),/X/);continue;}
  const svg=chartSvg(rows,{type,title:type});
  assert.ok(svg.includes('Custo'),type+' legend');
  assert.ok(svg.startsWith('<svg'),type);
 }
 const scatter=chartSvg([['X','Y1','Y2'],[1,2,3],[2,4,1],[3,6,2]],{type:'scatter',title:'s'});
 assert.equal((scatter.match(/<circle/g)||[]).length,6);
 const donut=chartSvg([['Nome','Valor'],['A',1],['B',3]],{type:'doughnut',title:'d'});
 assert.ok(donut.includes('>4</text>'));
});
test('stacked columns stack positive and negative values separately',()=>{
 const svg=chartSvg([['G','A','B'],['x',5,-2],['y',3,4]],{type:'stacked',title:'st'});
 assert.equal((svg.match(/<rect [^>]*><title>/g)||[]).length,4);
});
test('limits on series and rows',()=>{
 assert.throws(()=>chartData([['a','1','2','3','4','5','6','7'],['x',1,1,1,1,1,1,1]],'bar'));
 assert.throws(()=>chartData([['a','b']],'bar'));
});
