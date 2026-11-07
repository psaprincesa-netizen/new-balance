export async function mountFormAutomation(root,formId,{api,esc,notify,boards,openItem}){
  const token={};root.automationToken=token;root.innerHTML='<p role="status">Carregando automação…</p>';
  let source,setting;
  try{[source,setting]=await Promise.all([api('/api/items/'+formId),api('/api/items/'+formId+'/automation')]);}
  catch(error){if(root.isConnected&&root.automationToken===token)root.textContent=error.message;return;}
  if(!root.isConnected||root.automationToken!==token)return;
  const config=setting.config||{},choices=(source.content.fields||[]).map((field,index)=>({field,index})).filter(x=>x.field.type==='choice');
  root.innerHTML=`<h3>Nova resposta pública → tarefa</h3><p>Uma resposta recebida pelo link público cria uma tarefa no projeto escolhido. Os dois arquivos precisam pertencer a você. O título ficará visível às pessoas com acesso ao projeto. Respostas registradas apenas no editor não acionam esta regra.</p>
    <form id="automation-settings"><label class="checklist"><input type="checkbox" name="enabled" ${config.enabled?'checked':''}>Criar tarefa a cada nova resposta pública</label>
    <label class="field">Projeto de destino<select name="targetId" aria-label="Projeto de destino"><option value="">Escolha um projeto próprio…</option>${boards.filter(i=>i.owner===source.owner&&!i.deleted).map(i=>`<option value="${esc(i.id)}" ${i.id===config.targetId?'selected':''}>${esc(i.title)}</option>`).join('')}</select></label>
    <label class="field">Prefixo do título<input name="prefix" maxlength="100" value="${esc(config.prefix??'Nova resposta: ')}"></label>
    <label class="field">Texto usado no título<select name="titleQuestion" aria-label="Texto usado no título"><option value="">Título do formulário</option>${source.content.questions.map((q,i)=>`<option value="${i}" ${config.titleQuestion===i?'selected':''}>${i+1}: ${esc(q)}</option>`).join('')}</select></label>
    <label class="field">Prioridade da tarefa<select name="priority" aria-label="Prioridade da tarefa automática">${['Baixa','Normal','Alta','Urgente'].map(v=>`<option ${v===(config.priority||'Normal')?'selected':''}>${v}</option>`).join('')}</select></label>
    <label class="field">Executar somente quando<select name="whenQuestion" aria-label="Condição da automação"><option value="">Sempre</option>${choices.map(c=>`<option value="${c.index}" ${config.whenQuestion===c.index?'selected':''}>${c.index+1}: ${esc(source.content.questions[c.index])}</option>`).join('')}</select></label>
    <label class="field">Resposta exigida<select name="whenValue" aria-label="Resposta exigida para automação"></select></label>
    <p id="automation-error" role="alert" class="error"></p><button class="primary">Salvar automação</button></form>
    <div class="row"><h3>Execuções</h3><button id="automation-refresh">Atualizar painel</button></div><p id="automation-log-status" role="status"></p><div id="automation-runs"></div>`;
  const form=root.querySelector('form');
  const conditionOptions=()=>{const value=form.elements.whenQuestion.value,index=+value,field=source.content.fields?.[index];form.elements.whenValue.disabled=value==='';form.elements.whenValue.innerHTML=(field?.options||[]).map(o=>`<option value="${esc(o)}" ${o===config.whenValue?'selected':''}>${esc(o)}</option>`).join('');};
  form.elements.whenQuestion.onchange=conditionOptions;conditionOptions();
  const load=()=>mountFormAutomation(root,formId,{api,esc,notify,boards,openItem});
  form.onsubmit=async event=>{
    event.preventDefault();const button=form.querySelector('button');button.disabled=true;
    const data=Object.fromEntries(new FormData(form));data.enabled=form.elements.enabled.checked;data.version=source.version;
    for(const key of ['titleQuestion','whenQuestion'])data[key]=data[key]===''?null:Number(data[key]);
    try{await api('/api/items/'+formId+'/automation',data);notify('Automação salva. A regra vale para os próximos envios públicos.');await load();}
    catch(error){if(form.isConnected)root.querySelector('#automation-error').textContent=error.message;}
    finally{if(button.isConnected)button.disabled=false;}
  };
  root.querySelector('#automation-refresh').onclick=load;
  const showRuns=(data,offset=0)=>{
    const host=root.querySelector('#automation-runs');
    host.innerHTML=`${data.runs.length?'':'<p>Nenhuma execução registrada.</p>'}${data.runs.map(run=>`<article class="card"><strong>${esc(run.title)}</strong><span class="badge">${esc({completed:'Concluída',failed:'Falhou',skipped:'Ignorada',pending:'Em andamento'}[run.status]||run.status)}</span><p>${esc(run.detail)}</p><small>${esc(new Date(run.created).toLocaleString('pt-BR'))}</small>${run.status==='completed'?`<button data-run-open="${esc(run.target_id)}">Abrir projeto</button>`:''}${run.status==='failed'&&run.retryable?`<button data-run-retry="${esc(run.id)}">Reprocessar execução</button>`:''}</article>`).join('')}${offset?'<button id="automation-prev">Anteriores</button>':''}${data.next_offset!==null?'<button id="automation-next">Próximas execuções</button>':''}`;
    host.querySelectorAll('[data-run-open]').forEach(button=>button.onclick=()=>openItem(button.dataset.runOpen));
    host.querySelectorAll('[data-run-retry]').forEach(button=>button.onclick=async()=>{button.disabled=true;try{await api('/api/items/'+formId+'/automation/retry',{run_id:button.dataset.runRetry});await load();}catch(error){if(root.isConnected)root.querySelector('#automation-log-status').textContent=error.message;if(button.isConnected)button.disabled=false;}});
    const page=async n=>{try{const next=await api('/api/items/'+formId+'/automation?offset='+n);if(root.isConnected&&root.automationToken===token)showRuns(next,n);}catch(error){notify(error.message);}};
    host.querySelector('#automation-prev')?.addEventListener('click',()=>page(Math.max(0,offset-50)));
    host.querySelector('#automation-next')?.addEventListener('click',()=>page(data.next_offset));
  };showRuns(setting);
}
