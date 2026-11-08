const operations={count:'Contagem de registros',sum:'Soma',average:'Média',min:'Mínimo',max:'Máximo'};
const number=value=>value===null?'Sem valores':new Intl.NumberFormat('pt-BR',{maximumFractionDigits:6}).format(value);
export async function mountDashboard(root,{api,esc,notify,openItem}){
  const token={};root.dashboardToken=token;
  let state,sources,editing=null,alive=()=>root.isConnected&&root.dashboardToken===token;
  root.innerHTML='<p role="status">Carregando painel pessoal…</p>';
  try{[state,sources]=await Promise.all([api('/api/dashboard'),api('/api/dashboard/sources')]);}
  catch(error){if(alive())root.textContent=error.message;return;}
  if(!alive())return;
  async function persist(config){await api('/api/dashboard',{version:state.version,config});state=await api('/api/dashboard');if(alive())render();}
  const failure=error=>{if(alive()){const host=root.querySelector('#dashboard-status');if(host)host.textContent=error.message;notify(error.message);}};
  function exportResults(){
    const rows=[['Indicador','Fonte','Versão','Categoria','Valor','Registros','Erro']];
    for(const widget of state.config.widgets){const result=state.results.find(r=>r.id===widget.id)||{};for(const group of result.groups||[{label:'',value:result.value}])rows.push([widget.title,result.sourceTitle||'',result.sourceVersion??'',group.label,group.value??'',result.rows??'',result.error||'']);}
    const csv='\ufeff'+rows.map(row=>row.map(value=>{let text=String(value);if(/^[\s]*[=+@-]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';}).join(';')).join('\r\n');
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download='painel.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function resultMarkup(widget){
    const result=state.results.find(r=>r.id===widget.id)||{};
    if(result.error)return `<p role="status">${esc(result.error)}</p>`;
    let content=`<strong class="dashboard-value">${number(result.value)}</strong>`;
    if(result.groups){
      const maximum=Math.max(1,...result.groups.map(g=>Math.abs(g.value||0)));
      content=result.groups.length?`<table class="dashboard-table"><caption>${esc(operations[widget.operation])} por ${esc(widget.groupField.name)}</caption><thead><tr><th scope="col">Categoria</th><th scope="col">Valor</th></tr></thead><tbody>${result.groups.map(g=>`<tr><th scope="row">${esc(g.label||'(Vazio)')}</th><td><span class="dashboard-bar" style="width:${Math.round(Math.abs(g.value||0)/maximum*100)}%" aria-hidden="true"></span><span>${number(g.value)}</span></td></tr>`).join('')}</tbody></table>`:'<p>Nenhum registro corresponde ao filtro.</p>';
    }
    return `${content}<p class="muted">${esc(result.sourceTitle)} · versão ${result.sourceVersion} · ${result.rows} registros</p><button data-dashboard-open="${esc(widget.sourceId)}">Abrir fonte</button>`;
  }
  function render(){
    editing=null;root.innerHTML=`<div class="row between"><div><h2>${esc(state.config.title)}</h2><p class="muted">Painel pessoal · dados consultados agora · até 12 indicadores</p></div><div class="row"><button id="dashboard-refresh">Atualizar painel</button><button id="dashboard-export">Exportar indicadores CSV</button><button id="dashboard-add" class="primary" ${state.config.widgets.length>=12?'disabled':''}>Adicionar indicador</button></div></div><form id="dashboard-name" class="row"><label>Nome do painel<input name="title" aria-label="Nome do painel" maxlength="100" required value="${esc(state.config.title)}"></label><button>Renomear painel</button></form><p id="dashboard-status" role="status"></p><div id="dashboard-editor"></div><div class="dashboard-grid">${state.config.widgets.map(w=>`<article class="card"><h3>${esc(w.title)}</h3><p class="muted">${esc(operations[w.operation])}${w.filter?' · filtro: '+esc(w.filter.field.name)+' = '+esc(w.filter.value):''}</p>${resultMarkup(w)}<div class="row"><button data-dashboard-edit="${esc(w.id)}">Editar indicador ${esc(w.title)}</button><button data-dashboard-delete="${esc(w.id)}">Excluir indicador ${esc(w.title)}</button></div></article>`).join('')}</div>${state.config.widgets.length?'':'<p>Escolha uma tabela ou um projeto para criar seu primeiro indicador.</p>'}`;
    root.querySelector('#dashboard-name').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;try{await persist({...state.config,title:e.target.elements.title.value});}catch(error){failure(error);button.disabled=false;}};
    root.querySelector('#dashboard-add').onclick=()=>editor();root.querySelector('#dashboard-export').onclick=exportResults;
    root.querySelector('#dashboard-refresh').onclick=async()=>{try{await mountDashboard(root,{api,esc,notify,openItem});}catch(error){failure(error);}};
    root.querySelectorAll('[data-dashboard-open]').forEach(button=>button.onclick=()=>openItem(button.dataset.dashboardOpen));
    root.querySelectorAll('[data-dashboard-edit]').forEach(button=>button.onclick=()=>editor(state.config.widgets.find(w=>w.id===button.dataset.dashboardEdit)));
    root.querySelectorAll('[data-dashboard-delete]').forEach(button=>button.onclick=async()=>{button.disabled=true;try{await persist({...state.config,widgets:state.config.widgets.filter(w=>w.id!==button.dataset.dashboardDelete)});}catch(error){failure(error);button.disabled=false;}});
  }
  function editor(widget){
    editing=widget?.id||crypto.randomUUID();const host=root.querySelector('#dashboard-editor');
    host.innerHTML=`<form id="dashboard-widget" class="editor"><h3>${widget?'Editar':'Adicionar'} indicador</h3><p>Contagem inclui todos os registros filtrados. Medidas ignoram células vazias e recusam texto; use ponto decimal, sem separador de milhar. Agrupamentos aceitam até 50 categorias.</p><label class="field">Título do indicador<input name="title" maxlength="100" required value="${esc(widget?.title||'')}"></label><label class="field">Fonte do indicador<select aria-label="Fonte do indicador" name="sourceId" required><option value="">Escolha uma tabela ou projeto…</option>${sources.items.map(s=>`<option value="${esc(s.id)}" ${s.id===widget?.sourceId?'selected':''}>${esc(s.title)} (${s.kind==='board'?'Projeto':'Tabela'})</option>`).join('')}</select></label>${sources.limited?'<p>Exibindo as primeiras 500 fontes disponíveis.</p>':''}<label class="field">Cálculo<select aria-label="Cálculo" name="operation">${Object.entries(operations).map(([key,label])=>`<option value="${key}" ${key===widget?.operation?'selected':''}>${label}</option>`).join('')}</select></label><label class="field">Campo numérico<select aria-label="Campo numérico" name="valueField"></select></label><label class="field">Agrupar por<select aria-label="Agrupar por" name="groupField"></select></label><label class="field">Filtrar campo<select aria-label="Filtrar campo" name="filterField"></select></label><label class="field">Valor exato do filtro<input name="filterValue" maxlength="500" value="${esc(widget?.filter?.value||'')}"></label><p id="dashboard-widget-error" class="error" role="alert"></p><div class="row"><button class="primary">Salvar indicador</button><button type="button" id="dashboard-cancel">Cancelar indicador</button></div></form>`;
    const form=host.querySelector('form');
    function fields(initial=false){const source=sources.items.find(s=>s.id===form.elements.sourceId.value),columns=source?.columns||[];
      for(const [name,selected] of [['valueField',widget?.valueField],['groupField',widget?.groupField],['filterField',widget?.filter?.field]]){
        const previous=form.elements[name].value;form.elements[name].innerHTML=`<option value="">${name==='valueField'?'Escolha um campo…':name==='groupField'?'Sem agrupamento':'Sem filtro'}</option>`+columns.map((column,index)=>`<option value="${index}" ${initial&&selected?.index===index&&selected?.name===column?'selected':''} ${columns.filter(c=>c===column).length!==1?'disabled':''}>${esc(column)}${columns.filter(c=>c===column).length!==1?' (ambíguo)':''}</option>`).join('');
        if(!initial&&previous!==''&&columns[+previous]!==undefined)form.elements[name].value=previous;
      }form.elements.valueField.disabled=form.elements.operation.value==='count';form.elements.valueField.required=!form.elements.valueField.disabled;form.elements.filterValue.disabled=form.elements.filterField.value==='';
    }
    form.elements.sourceId.onchange=()=>fields();form.elements.operation.onchange=()=>{form.elements.valueField.disabled=form.elements.operation.value==='count';form.elements.valueField.required=!form.elements.valueField.disabled;};form.elements.filterField.onchange=()=>{form.elements.filterValue.disabled=form.elements.filterField.value==='';};fields(true);
    host.querySelector('#dashboard-cancel').onclick=()=>{host.innerHTML='';editing=null;};
    form.onsubmit=async event=>{event.preventDefault();const button=form.querySelector('button');button.disabled=true;const source=sources.items.find(s=>s.id===form.elements.sourceId.value);if(!source){button.disabled=false;return;}const field=name=>{const value=form.elements[name].value;return value===''?null:{index:+value,name:source.columns[+value]};};const next={id:editing,title:form.elements.title.value,sourceId:source.id,operation:form.elements.operation.value,valueField:form.elements.operation.value==='count'?null:field('valueField'),groupField:field('groupField'),filter:field('filterField')?{field:field('filterField'),value:form.elements.filterValue.value}:null};
      try{await persist({...state.config,widgets:widget?state.config.widgets.map(w=>w.id===widget.id?next:w):[...state.config.widgets,next]});notify('Indicador salvo.');}catch(error){if(form.isConnected)form.querySelector('#dashboard-widget-error').textContent=error.message;button.disabled=false;}
    };form.elements.title.focus();
  }
  render();
}
