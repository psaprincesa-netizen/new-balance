export function parseDataRange(address){
  const m=/^([A-Z]{1,3})([1-9][0-9]{0,5})(?::([A-Z]{1,3})([1-9][0-9]{0,5}))?$/.exec(String(address).trim().toUpperCase());
  if(!m)throw Error('Use uma célula ou intervalo, como A1 ou A1:D100.');
  const col=s=>[...s].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0)-1;
  const startRow=+m[2]-1,endRow=+(m[4]||m[2])-1,startColumn=col(m[1]),endColumn=col(m[3]||m[1]);
  const height=endRow-startRow+1,width=endColumn-startColumn+1;
  if(height<1||width<1||height>10000||width>256||height*width>50000||endRow>=100000||endColumn>=1024)throw Error('Selecione até 10 mil linhas, 256 colunas e 50 mil células em ordem crescente.');
  return {startRow,endRow,startColumn,endColumn,height,width};
}
// Transform computed values into a separate destination; never execute input text.
export function transformRows(rows,operation,{separator=',',search='',replacement='',header=false,caseSensitive=true}={}) {
  if(!rows.length||!rows[0]?.length)throw Error('Selecione células com dados.');
  const width=Math.max(...rows.map(r=>r.length));
  let data=rows.map(r=>Array.from({length:width},(_,i)=>r[i]??''));
  const empty=v=>v===''||v==null;
  if(operation==='trim')data=data.map(r=>r.map(v=>typeof v==='string'?v.replace(/\s+/gu,' ').trim():v));
  else if(operation==='replace'){
    if(!search)throw Error('Preencha o texto a localizar.');
    const pattern=new RegExp(search.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),caseSensitive?'g':'gi');
    data=data.map(r=>r.map(v=>typeof v==='string'?v.replace(pattern,()=>replacement):v));
  }else if(operation==='unique'){
    const seen=new Set();data=data.filter((r,i)=>{if(header&&i===0)return true;const key=JSON.stringify(r.map(v=>typeof v==='string'&&!caseSensitive?v.toLocaleLowerCase('pt-BR'):v));if(seen.has(key))return false;seen.add(key);return true;});
  }else if(operation==='empty')data=data.filter((r,i)=>(header&&i===0)||r.some(v=>!empty(v)));
  else if(operation==='transpose')data=Array.from({length:width},(_,c)=>data.map(r=>r[c]));
  else if(operation==='split'){
    if(width!==1)throw Error('Selecione somente uma coluna para dividir.');
    if(!separator)throw Error('Informe o separador.');
    data=data.map(r=>String(r[0]).split(separator));const w=Math.max(...data.map(r=>r.length));data=data.map(r=>Array.from({length:w},(_,c)=>r[c]??''));
  }else throw Error('Transformação desconhecida.');
  if(!data.length)throw Error('O resultado não contém linhas.');
  if(data.length>10000||data[0].length>256||data.length*data[0].length>50000)throw Error('O resultado excede 10 mil linhas, 256 colunas ou 50 mil células.');
  return data;
}
export function rangeStatistics(rows){
  let filled=0,numbers=0,sum=0,min=null,max=null;
  for(const row of rows)for(const value of row){if(value!==''&&value!=null)filled++;if(typeof value==='number'&&Number.isFinite(value)){numbers++;sum+=value;min=min===null?value:Math.min(min,value);max=max===null?value:Math.max(max,value);}}
  return {filled,numbers,sum,average:numbers?sum/numbers:null,min,max};
}
export function mountSheetTools(root,sheet,{address,dialog,bind,close,escape:esc,notify,readOnly}){
  const options={trim:'Remover espaços extras',unique:'Remover linhas duplicadas',empty:'Remover linhas vazias',split:'Dividir texto em colunas',transpose:'Transpor linhas e colunas',replace:'Localizar e substituir'};
  const toolbar=document.createElement('div');toolbar.className='toolbar sheet-tools';toolbar.innerHTML='<button id="sheet-transform">Limpar e transformar dados</button><button id="sheet-stats">Estatísticas do intervalo</button>';root.querySelector('#spreadsheet').before(toolbar);
  bind('sheet-stats',async()=>{try{await sheet.flush();const stats=rangeStatistics(sheet.read(address()).values);dialog('<h2>Estatísticas de '+esc(address())+'</h2><dl>'+Object.entries({filled:'Células preenchidas',numbers:'Valores numéricos',sum:'Soma',average:'Média',min:'Mínimo',max:'Máximo'}).map(([k,v])=>'<dt>'+v+'</dt><dd>'+(stats[k]===null?'—':stats[k].toLocaleString('pt-BR'))+'</dd>').join('')+'</dl><button id="stats-close">Fechar</button>',()=>bind('stats-close',close));}catch(e){notify(e.message);}});
  root.querySelector('#sheet-transform').disabled=readOnly;
  bind('sheet-transform',()=>{
    if(readOnly)return;
    dialog(`<h2>Limpar e transformar dados</h2><form id="transform-form"><label class="field">Origem<input name="source" value="${esc(address())}" required></label><label class="field">Operação<select name="operation">${Object.entries(options).map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select></label><label class="field">Célula de destino vazia<input name="target" placeholder="Ex.: H1" required></label><label class="field">Separador (para dividir)<input name="separator" value=","></label><label class="field">Localizar<input name="search"></label><label class="field">Substituir por<input name="replacement"></label><label><input name="header" type="checkbox"> Primeira linha é cabeçalho</label><label><input name="caseSensitive" type="checkbox" checked> Diferenciar maiúsculas</label><p>Cria uma cópia dos valores calculados em células vazias da mesma aba. Fórmulas e formatação da origem não são copiadas. Use Desfazer na barra para reverter.</p><p id="transform-error" role="alert"></p><button class="primary">Criar resultado</button></form>`,()=>bind('transform-form',async e=>{e.preventDefault();try{await sheet.flush();const f=new FormData(e.target),values=transformRows(sheet.read(String(f.get('source')).trim().toUpperCase()).values,f.get('operation'),{separator:f.get('separator'),search:f.get('search'),replacement:f.get('replacement'),header:f.has('header'),caseSensitive:f.has('caseSensitive')});await sheet.writeEmpty(String(f.get('target')).trim().toUpperCase(),values);close();notify(`Resultado criado: ${values.length} linhas × ${values[0].length} colunas.`);}catch(err){document.querySelector('#transform-error').textContent=err.message;}},'submit'));
  });
}
