import {captureBaseline, baselineComparison, resourceCapacity} from './project-planning.js';

export function mountProjectPlanning(root, content, {esc, dirty, rerender, confirm, notify, readOnly}) {
  const money = cents => (cents/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
  const number = n => n.toLocaleString('pt-BR',{maximumFractionDigits:2});
  const section = document.createElement('section');section.id = 'project-planning';
  const capacity = resourceCapacity(content.tasks, content.resources);
  const comparison = baselineComparison(content.tasks, content.baseline);
  section.innerHTML = `<details id="project-capacity"><summary>Capacidade dos responsáveis</summary>
    <p>Horas planejadas distribuídas igualmente pelos dias corridos do cronograma, incluindo fins de semana. Capacidade padrão: 8 h/dia. Alterar a capacidade não muda datas ou horas das tarefas.</p>
    <form id="resource-capacity-form" class="toolbar"><label>Responsável pela capacidade<input name="name" maxlength="100" required list="project-assignees"></label><datalist id="project-assignees">${[...new Set(content.tasks.map(t=>t.assignee?.trim()).filter(Boolean))].map(name=>`<option value="${esc(name)}"></option>`).join('')}</datalist><label>Capacidade diária (horas)<input name="dailyHours" type="number" min="0" max="24" step="0.01" value="8" required></label><button ${readOnly?'disabled':''}>Definir capacidade</button></form>
    <ul>${(content.resources||[]).map((r,i)=>`<li>${esc(r.name)}: ${number(r.dailyHours)} h/dia <button data-remove-resource="${i}" ${readOnly?'disabled':''}>Usar padrão para ${esc(r.name)}</button></li>`).join('')}</ul>
    <div class="table-wrap"><table><thead><tr><th>Responsável</th><th>Capacidade h/dia</th><th>Pico h/dia</th><th>Dias acima da capacidade</th></tr></thead><tbody>${capacity.rows.map(r=>`<tr><td>${esc(r.name)}</td><td>${number(r.capacity)}</td><td>${number(r.peak)}</td><td>${r.overloadedDays}</td></tr>`).join('')}</tbody></table></div>
    ${capacity.rows.filter(r=>r.conflicts.length).map(r=>`<details><summary>Sobrecarga: ${esc(r.name)} (${r.overloadedDays} dias)</summary><ul>${r.conflicts.map(f=>`<li>${f.start} a ${f.end}: ${number(f.dailyHours)} h/dia</li>`).join('')}</ul></details>`).join('')}
    ${capacity.unallocated.length?`<p role="status">Horas sem alocação por falta de responsável ou datas: ${capacity.unallocated.map(esc).join(', ')}.</p>`:''}</details>
    <details id="project-baseline"><summary>Linha de base e desvios</summary><p>Registre o cronograma e orçamento aprovados para comparar mudanças. O registro fica fixo até ser substituído. Use Salvar para persistir.</p><button id="capture-baseline" ${readOnly?'disabled':''}>${comparison?'Substituir linha de base':'Registrar linha de base'}</button>
    ${comparison?`<p>Registrada em ${esc(new Date(content.baseline.capturedAt).toLocaleString('pt-BR'))}. Desvio do orçamento planejado: <strong id="baseline-cost-delta">${money(comparison.plannedDelta)}</strong>. Realizado contra a base: ${money(comparison.actualDelta)}. Desvio de horas planejadas: ${number(comparison.hoursDelta)}.</p><div class="table-wrap"><table><thead><tr><th>Tarefa</th><th>Situação</th><th>Prazo da base</th><th>Prazo atual</th><th>Desvio (dias)</th><th>Desvio de custo planejado</th></tr></thead><tbody>${comparison.rows.map(r=>`<tr><td>${esc(r.title)}</td><td>${r.state}</td><td>${r.beforeDue||'Sem data'}</td><td>${r.due||'Sem data'}</td><td>${r.delayDays??'—'}</td><td>${money(r.costDelta)}</td></tr>`).join('')}</tbody></table></div>`:'<p>Nenhuma linha de base registrada.</p>'}</details>`;
  root.append(section);
  section.querySelector('#capture-baseline').onclick = async () => {
    if (readOnly) return;
    if (content.baseline && !await confirm('Substituir linha de base?', 'O cronograma e o orçamento atuais substituirão a referência anterior. O histórico de versões permanece disponível após salvar.')) return;
    try {content.baseline = captureBaseline(content.tasks);dirty();rerender();notify('Linha de base registrada. Salve o projeto para persistir.');} catch(e) {notify(e.message);}
  };
  section.querySelector('#resource-capacity-form').onsubmit = event => {
    event.preventDefault();if(readOnly)return;
    const form = new FormData(event.target), name = form.get('name').trim(), dailyHours = Number(form.get('dailyHours'));
    if(!name || !Number.isFinite(dailyHours) || dailyHours < 0 || dailyHours > 24) return notify('Informe responsável e capacidade de 0 a 24 horas.');
    content.resources ??= [];
    const previous = content.resources.find(r=>r.name===name);
    if(previous) previous.dailyHours = dailyHours;
    else {if(content.resources.length>=200)return notify('Limite de 200 responsáveis com capacidade personalizada.');content.resources.push({name,dailyHours});}
    dirty();rerender();
  };
  section.querySelectorAll('[data-remove-resource]').forEach(button=>button.onclick=()=>{if(readOnly)return;content.resources.splice(+button.dataset.removeResource,1);dirty();rerender();});
  if(readOnly)section.querySelectorAll('input,button').forEach(n=>n.disabled=true);
}
