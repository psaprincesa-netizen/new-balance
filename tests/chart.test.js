import test from 'node:test';
import assert from 'node:assert/strict';
import {chartData,chartSvg} from '../web/chart.js';
test('charts use numeric cells, handle negative values and escape labels',()=>{
 const rows=[['Nome','Valor'],['<script>',-20],['B',30]];
 assert.equal(chartData(rows,'bar')[1].value,30);
 const svg=chartSvg(rows,{type:'bar',title:'<script>'});assert.ok(svg.includes('&lt;script&gt;'));assert.ok(!svg.includes('<script>'));
 assert.throws(()=>chartData(rows,'pie'));
 assert.throws(()=>chartData([['Nome','Valor'],['A','#DIV/0!']],'line'));
 assert.ok(chartSvg([['Nome','Valor'],['A',20]],{type:'pie',title:'Parte'}).includes('<circle'));
});
