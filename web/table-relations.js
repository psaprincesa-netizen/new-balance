export function mountTableRelations(root,item,{api,esc,dirty,isDirty,dialog,close,notify,items,render}) {
  const content=item.content,readOnly=item.role==='read';
  const section=document.createElement('section');section.id='table-relations';
  const relations=content.relations||[];
  section.innerHTML=`<h2>Relacionamentos entre tabelas</h2><p>Consulte registros de outra tabela que tenham exatamente o mesmo valor em um campo. A consulta usa arquivos salvos e exige acesso às duas tabelas. Valores vazios não são relacionados.</p>${readOnly?'':'<button id="add-table-relation">Vincular tabela</button>'}${relations.map((r,i)=>`<article class="card"><h3>${esc(r.name)}</h3><p>Campo de origem: ${esc(r.sourceName)} → campo vinculado: ${esc(r.targetName)}</p><label>Registro de origem<select data-relation-row="${i}" aria-label="Registro para ${esc(r.name)}">${content.rows.map((row,n)=>`<option value="${n}">${n+1}: ${esc(row[r.sourceColumn]||'(vazio)')}</option>`).join('')}</select></label><button data-relation-query="${i}" ${content.rows.length?'':'disabled'}>Consultar ${esc(r.name)}</button>${readOnly?'':`<button data-relation-remove="${i}" class="danger">Remover vínculo ${esc(r.name)}</button>`}</article>`).join('')}`;
  root.append(section);
  const requireSaved=()=>{if(item.unsaved||isDirty()){notify('Salve a tabela antes de configurar ou consultar relacionamentos.');return false;}return true;};
  section.querySelector('#add-table-relation')?.addEventListener('click',()=>{
    if(readOnly||!requireSaved())return;
    if(relations.length>=10)return notify('Limite de dez relacionamentos por tabela.');
    const available=items.filter(t=>t.kind==='table'&&t.id!==item.id&&!t.deleted);
    dialog(`<h2>Vincular tabela</h2><form id="table-relation-form"><label class="field">Nome do relacionamento<input name="name" maxlength="200" required></label><label class="field">Campo desta tabela<select name="sourceColumn" aria-label="Campo desta tabela">${content.columns.map((name,i)=>`<option value="${i}">${esc(name)}</option>`).join('')}</select></label><label class="field">Tabela vinculada<select name="targetId" aria-label="Tabela vinculada" required><option value="">Selecione…</option>${available.map(t=>`<option value="${esc(t.id)}">${esc(t.title)}</option>`).join('')}</select></label><label class="field">Campo da tabela vinculada<select name="targetColumn" aria-label="Campo da tabela vinculada" required disabled></select></label><p id="relation-error" class="error" role="alert"></p><button id="relation-submit" disabled>Criar vínculo</button><button id="relation-cancel" type="button">Cancelar</button></form>`,()=>{
      const form=document.querySelector('#table-relation-form'),error=document.querySelector('#relation-error');let target=null,sequence=0;
      form.querySelector('#relation-cancel').onclick=close;
      form.elements.targetId.onchange=async()=>{
        const request=++sequence;target=null;form.elements.targetColumn.disabled=true;form.querySelector('#relation-submit').disabled=true;error.textContent='';
        if(!form.elements.targetId.value)return;
        try{const selected=await api('/api/items/'+form.elements.targetId.value);if(request!==sequence||!form.isConnected)return;
          if(selected.kind!=='table'||selected.deleted)throw Error('Tabela indisponível.');target=selected;
          form.elements.targetColumn.innerHTML=target.content.columns.map((name,i)=>`<option value="${i}">${esc(name)}</option>`).join('');
          form.elements.targetColumn.disabled=false;form.querySelector('#relation-submit').disabled=false;
        }catch(e){if(form.isConnected&&request===sequence)error.textContent=e.message;}
      };
      form.onsubmit=e=>{e.preventDefault();if(!target)return;const data=Object.fromEntries(new FormData(form));const sourceColumn=+data.sourceColumn,targetColumn=+data.targetColumn;
        if(!data.name.trim()){error.textContent='Informe um nome para o relacionamento.';return;}
        if(!content.columns[sourceColumn].trim()||!target.content.columns[targetColumn].trim()||content.columns.filter(n=>n===content.columns[sourceColumn]).length!==1||target.content.columns.filter(n=>n===target.content.columns[targetColumn]).length!==1){error.textContent='Os campos escolhidos precisam ter nomes preenchidos e únicos nas respectivas tabelas.';return;}
        (content.relations??=[]).push({id:crypto.randomUUID(),name:data.name.trim(),sourceColumn,sourceName:content.columns[sourceColumn],targetId:target.id,targetColumn,targetName:target.content.columns[targetColumn]});
        close();dirty();render();notify('Vínculo criado. Salve para persistir.');
      };
    });
  });
  section.querySelectorAll('[data-relation-remove]').forEach(button=>button.onclick=()=>{if(readOnly)return;content.relations.splice(+button.dataset.relationRemove,1);dirty();render();});
  section.querySelectorAll('[data-relation-query]').forEach(button=>button.onclick=async()=>{
    if(!requireSaved())return;const index=+button.dataset.relationQuery,relation=relations[index],row=section.querySelector(`[data-relation-row="${index}"]`).value;
    const show=async offset=>{
      button.disabled=true;
      try{const result=await api(`/api/items/${item.id}/related?relation=${encodeURIComponent(relation.id)}&row=${row}&version=${item.version}&offset=${offset}`);
        if(!root.isConnected)return;
        dialog(`<h2>${esc(relation.name)}</h2><p>${esc(result.title)} · ${result.total} registro(s) correspondente(s). Exibindo ${result.rows.length?offset+1:0} a ${offset+result.rows.length}.</p><div class="table-wrap"><table><thead><tr>${result.columns.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${result.rows.map(r=>`<tr>${r.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${offset?'<button id="relation-prev">Anteriores</button>':''}${result.next_offset!==null?'<button id="relation-next">Próximos</button>':''}<button id="relation-close">Fechar</button>`,()=>{
          document.querySelector('#relation-close').onclick=close;
          document.querySelector('#relation-prev')?.addEventListener('click',()=>show(Math.max(0,offset-50)));
          document.querySelector('#relation-next')?.addEventListener('click',()=>show(result.next_offset));
        });
      }catch(error){notify(error.message);}finally{if(button.isConnected)button.disabled=false;}
    };await show(0);
  });
}
