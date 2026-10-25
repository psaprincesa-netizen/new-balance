// Pivot tables operate on cell values; no user code is evaluated.
export const AGGREGATES={sum:'Soma',avg:'Média',count:'Contagem preenchida',rows:'Contagem de linhas',min:'Mínimo',max:'Máximo'};
export function parsePivotRange(address){
  const m=/^([A-Z]{1,3})([1-9]\d{0,5}):([A-Z]{1,3})([1-9]\d{0,5})$/.exec(String(address).trim().toUpperCase());
  if(!m)throw Error('Use um intervalo com cabeçalho, como A1:D100.');
  const col=s=>[...s].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0)-1;
  const result={startRow:+m[2]-1,endRow:+m[4]-1,startColumn:col(m[1]),endColumn:col(m[3])};
  const height=result.endRow-result.startRow+1,width=result.endColumn-result.startColumn+1;
  if(height<2||width<1||width>256||height*width>50000||result.endRow>=100000||result.endColumn>=1024)throw Error('A fonte aceita cabeçalho e dados, até 256 colunas e 50 mil células.');
  return {...result,height,width};
}
export function pivotHeaders(rows){
  if(!Array.isArray(rows)||rows.length<2||!Array.isArray(rows[0])||!rows[0].length||rows.length*rows[0].length>50000)throw Error('Selecione cabeçalho e dados, até 50 mil células.');
  const names=rows[0].map(v=>String(v??'').trim());
  if(names.some(v=>!v)||new Set(names).size!==names.length)throw Error('Cada coluna da fonte precisa de um cabeçalho preenchido e único.');
  return names;
}
const label=v=>v==null||v===''?'(vazio)':String(v);
const key=v=>JSON.stringify([v==null||v===''?'empty':typeof v,v==null||v===''?null:v]);
const blank=v=>v==null||v==='';
function matches(value,filter){
  if(typeof value==='number'&&/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?$/.test(filter))return Number(filter)===value;
  return String(value??'')===filter;
}
const fresh=()=>({rows:0,count:0,n:0,sum:0,min:Infinity,max:-Infinity});
function accumulate(s,value){s.rows++;if(!blank(value))s.count++;if(typeof value==='number'&&Number.isFinite(value)){s.n++;s.sum+=value;s.min=Math.min(s.min,value);s.max=Math.max(s.max,value);}}
const total=(s,op)=>{const value=op==='rows'?s.rows:op==='count'?s.count:op==='sum'?s.sum:!s.n?null:op==='avg'?s.sum/s.n:op==='min'?s.min:s.max;if(value!==null&&!Number.isFinite(value))throw Error('O resultado excede o limite numérico. Reduza os valores da fonte.');return value;};
export function calculatePivot(rows,config){
  const headers=pivotHeaders(rows),width=headers.length;
  for(const field of [config.rowField,config.valueField,...(config.columnField==null?[]:[config.columnField]),...(config.filterField==null?[]:[config.filterField])])if(!Number.isInteger(field)||field<0||field>=width)throw Error('Um campo da tabela dinâmica não existe na fonte.');
  if(!Object.hasOwn(AGGREGATES,config.aggregate))throw Error('Agregação inválida.');
  const rowGroups=new Map(),columnGroups=new Map(),cells=new Map(),rowTotals=new Map(),colTotals=new Map(),grand=fresh(),records=[];
  for(let i=1;i<rows.length;i++){
    const row=rows[i];if(!row.some(v=>!blank(v)))continue;
    if(config.filterField!=null&&!matches(row[config.filterField],config.filterValue))continue;
    const value=row[config.valueField];
    if(!['rows','count'].includes(config.aggregate)&&typeof value==='string'&&/^#(?:DIV\/0!|VALUE!|REF!|NAME\?|NUM!|N\/A|SPILL!|CALC!)/.test(value))throw Error('A fonte contém erros de fórmula no campo de valores. Corrija-os para calcular o resumo.');
    const r=key(row[config.rowField]),c=config.columnField==null?'all':key(row[config.columnField]);
    rowGroups.set(r,label(row[config.rowField]));columnGroups.set(c,config.columnField==null?AGGREGATES[config.aggregate]:label(row[config.columnField]));
    if((rowGroups.size+2)*(columnGroups.size+2)>10000)throw Error('O resumo excede 10 mil células. Use um filtro ou menos categorias.');
    const cellKey=JSON.stringify([r,c]);
    if(!cells.has(cellKey))cells.set(cellKey,fresh());if(!rowTotals.has(r))rowTotals.set(r,fresh());if(!colTotals.has(c))colTotals.set(c,fresh());
    for(const state of [cells.get(cellKey),rowTotals.get(r),colTotals.get(c),grand])accumulate(state,value);
    records.push({index:i,rowKey:r,columnKey:c});
  }
  const columns=[...columnGroups.keys()];if(!columns.length)columns.push('all');
  const rowKeys=[...rowGroups.keys()];
  if(config.sort==='asc'||config.sort==='desc')rowKeys.sort((a,b)=>((total(rowTotals.get(a),config.aggregate)??0)-(total(rowTotals.get(b),config.aggregate)??0))*(config.sort==='asc'?1:-1));
  const withColumns=config.columnField!=null;
  const header=[headers[config.rowField],...columns.map(k=>columnGroups.get(k)||AGGREGATES[config.aggregate]),...(withColumns?['Total geral']:[])];
  const values=rowKeys.map(r=>[rowGroups.get(r),...columns.map(c=>total(cells.get(JSON.stringify([r,c]))||fresh(),config.aggregate)),...(withColumns?[total(rowTotals.get(r),config.aggregate)]:[])]);
  values.push(['Total geral',...columns.map(c=>total(colTotals.get(c)||fresh(),config.aggregate)),...(withColumns?[total(grand,config.aggregate)]:[])]);
  return {headers:header,rows:values,rowKeys,columnKeys:columns,records,sourceHeaders:headers,count:grand.rows,numericCount:grand.n};
}
export function pivotDetails(source,result,rowIndex,columnIndex){
  const rk=rowIndex<result.rowKeys.length?result.rowKeys[rowIndex]:null;
  const ck=columnIndex<result.columnKeys.length?result.columnKeys[columnIndex]:null;
  return [source[0],...result.records.filter(r=>(rk==null||r.rowKey===rk)&&(ck==null||r.columnKey===ck)).map(r=>source[r.index])];
}
export const safeCsvRows=rows=>rows.map(row=>row.map(value=>typeof value==='string'&&/^[=+@\-\t\r]/.test(value)?"'"+value:value));
