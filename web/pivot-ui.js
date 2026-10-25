import {AGGREGATES,parsePivotRange,pivotHeaders,calculatePivot,pivotDetails,safeCsvRows} from './pivot.js';
import {toCSV} from './formula.js';
export function mountPivots({root,content,spreadsheet,readOnly,dirty,dialog,closeDialog,notify,download,escapeHtml:esc}){
  const panel=root.querySelector('#sheet-pivots');
  let cached=[];
  const source=p=>{parsePivotRange(p.range);return spreadsheet.rangeRows(p.range,p.sheetId);};
  function table(rows,buttons=false,pivotIndex=0){return `<div class="pivot-scroll"><table class="pivot-table"><thead><tr>${rows[0].map(v=>'<th scope="col">'+esc(v)+'</th>').join('')}</tr></thead><tbody>${rows.slice(1).map((row,r)=>'<tr>'+row.map((v,c)=>c===0?'<th scope="row">'+esc(v??'')+'</th>':`<td>${buttons?`<button data-pivot-detail="${pivotIndex}:${r}:${c-1}" aria-label="Registros de ${esc(row[0])}, ${esc(rows[0][c])}">${esc(v??'—')}</button>`:esc(v??'')}</td>`).join('')+'</tr>').join('')}</tbody></table></div>`;}
  function render(){
    if(!root.isConnected)return;
    cached=[];
    panel.innerHTML=(content.pivots||[]).map((p,i)=>{
      let body;
      try{const data=source(p),result=calculatePivot(data,p);cached[i]={data,result};body=`<p class="muted">${result.count} registros · ${result.numericCount} valores numéricos · ${esc(AGGREGATES[p.aggregate])}. Clique em um resultado para consultar os registros.</p>${table([result.headers,...result.rows],true,i)}`;}
      catch(e){body='<p role="alert" class="error">'+esc(e.message)+'</p>';}
      return `<article class="pivot-card" data-pivot-card="${i}"><div class="toolbar"><h3>${esc(p.title)}</h3><span>${esc(p.range)}</span><button data-pivot-csv="${i}" ${cached[i]?'':'disabled'}>Baixar resumo CSV</button>${!readOnly?`<button data-pivot-edit="${i}">Configurar resumo</button><button data-pivot-remove="${i}">Excluir resumo</button>`:''}</div>${body}</article>`;
    }).join('');
    panel.querySelectorAll('[data-pivot-csv]').forEach(el=>el.onclick=()=>{const i=+el.dataset.pivotCsv,r=cached[i].result;download(content.pivots[i].title+'.csv',toCSV(safeCsvRows([r.headers,...r.rows])),'text/csv');});
    panel.querySelectorAll('[data-pivot-edit]').forEach(el=>el.onclick=()=>open(+el.dataset.pivotEdit));
    panel.querySelectorAll('[data-pivot-remove]').forEach(el=>el.onclick=()=>{content.pivots.splice(+el.dataset.pivotRemove,1);dirty();render();});
    panel.querySelectorAll('[data-pivot-detail]').forEach(el=>el.onclick=()=>{
      const [i,r,c]=el.dataset.pivotDetail.split(':').map(Number),entry=cached[i],rows=pivotDetails(entry.data,entry.result,r,c);
      dialog(`<h2>Registros de origem</h2><p>${rows.length-1} registros. Exibindo até 200.</p>${table(rows.slice(0,201))}<button id="pivot-details-csv">Baixar todos os registros CSV</button><button id="pivot-details-close">Fechar</button>`,()=>{
        document.querySelector('#pivot-details-csv').onclick=()=>download('registros.csv',toCSV(safeCsvRows(rows)),'text/csv');document.querySelector('#pivot-details-close').onclick=closeDialog;
      });
    });
  }
  async function open(index=null){
    if(readOnly)return;
    try{
      await spreadsheet.flush();
      if(index==null&&(content.pivots||[]).length>=10)throw Error('Limite de dez tabelas dinâmicas por arquivo.');
      const previous=index==null?null:content.pivots[index],sheets=spreadsheet.listSheets();
      const selected=previous?.sheetId||spreadsheet.activeSheetId();
      const range=previous?.range||root.querySelector('#sheet-address').value.trim().toUpperCase();
      dialog(`<h2>${previous?'Configurar':'Criar'} tabela dinâmica</h2><form id="pivot-form"><label class="field">Título do resumo<input name="title" maxlength="100" value="${esc(previous?.title||'Resumo dinâmico')}" required></label><label class="field">Aba de origem<select name="sheetId" aria-label="Aba de origem">${sheets.map(s=>`<option value="${esc(s.id)}" ${s.id===selected?'selected':''}>${esc(s.name)}</option>`).join('')}</select></label><label class="field">Intervalo da fonte<input name="range" value="${esc(range.includes(':')?range:'A1:C10')}" required></label><button type="button" id="pivot-fields-load">Carregar campos</button><div id="pivot-fields"></div><p>Até 50 mil células na fonte. O resumo inclui todas as linhas do intervalo; filtros da grade não alteram o resumo. Use o filtro abaixo. Inserir ou excluir linhas não ajusta o endereço da fonte automaticamente.</p><p>O XLSX leva os resultados como tabelas comuns. A configuração dinâmica fica no DRAP e no backup JSON.</p><p id="pivot-error" role="alert" class="error"></p><button class="primary" id="pivot-submit" disabled>Salvar tabela dinâmica</button></form>`,()=>{
        const form=document.querySelector('#pivot-form'),fields=document.querySelector('#pivot-fields'),error=document.querySelector('#pivot-error');let loaded=null;
        const invalidate=()=>{loaded=null;fields.innerHTML='';document.querySelector('#pivot-submit').disabled=true;};
        form.elements.range.oninput=invalidate;form.elements.sheetId.onchange=invalidate;
        function load(){try{
          const range=form.elements.range.value.trim().toUpperCase(),sheetId=form.elements.sheetId.value;
          const data=source({range,sheetId}),headers=pivotHeaders(data);loaded={range,sheetId,data};
          const options=(value,empty=false)=>(empty?'<option value="">Nenhum</option>':'')+headers.map((h,i)=>`<option value="${i}" ${i===value?'selected':''}>${esc(h)}</option>`).join('');
          fields.innerHTML=`<label class="field">Agrupar linhas por<select name="rowField" aria-label="Agrupar linhas por">${options(previous?.rowField??0)}</select></label><label class="field">Agrupar colunas por<select name="columnField" aria-label="Agrupar colunas por">${options(previous?.columnField??null,true)}</select></label><label class="field">Campo de valores<select name="valueField" aria-label="Campo de valores">${options(previous?.valueField??Math.min(1,headers.length-1))}</select></label><label class="field">Cálculo<select name="aggregate" aria-label="Cálculo">${Object.entries(AGGREGATES).map(([v,label])=>`<option value="${v}" ${v===(previous?.aggregate||'sum')?'selected':''}>${label}</option>`).join('')}</select></label><label class="field">Ordem dos grupos<select name="sort" aria-label="Ordem dos grupos"><option value="source">Ordem da fonte</option><option value="asc">Total crescente</option><option value="desc">Total decrescente</option></select></label><label class="field">Filtrar campo<select name="filterField" aria-label="Filtrar campo">${options(previous?.filterField??null,true)}</select></label><label class="field">Valor do filtro<input name="filterValue" maxlength="1000" value="${esc(previous?.filterValue||'')}" placeholder="Correspondência exata; vazio para células vazias"></label>`;
          form.elements.sort.value=previous?.sort||'source';error.textContent='';document.querySelector('#pivot-submit').disabled=false;
        }catch(e){invalidate();error.textContent=e.message;}}
        document.querySelector('#pivot-fields-load').onclick=load;load();
        form.onsubmit=async e=>{e.preventDefault();const submit=form.querySelector('#pivot-submit');if(submit.disabled)return;submit.disabled=true;submit.textContent='Calculando…';try{
          if(!loaded)throw Error('Carregue os campos da fonte.');
          await spreadsheet.flush();const data=new FormData(form),p={id:previous?.id||crypto.randomUUID(),title:String(data.get('title')).trim(),sheetId:loaded.sheetId,range:loaded.range,rowField:+data.get('rowField'),valueField:+data.get('valueField'),columnField:data.get('columnField')===''?null:+data.get('columnField'),aggregate:data.get('aggregate'),sort:data.get('sort'),filterField:data.get('filterField')===''?null:+data.get('filterField'),filterValue:String(data.get('filterValue'))};
          if(!p.title)throw Error('Preencha o título.');calculatePivot(source(p),p);
          content.pivots??=[];if(index==null)content.pivots.push(p);else content.pivots[index]=p;
          closeDialog();dirty();render();
        }catch(e){error.textContent=e.message;submit.disabled=false;submit.textContent='Salvar tabela dinâmica';}};
      });
    }catch(e){notify(e.message);}
  }
  root.querySelector('#sheet-pivot-add').onclick=()=>open();
  render();return {render};
}
