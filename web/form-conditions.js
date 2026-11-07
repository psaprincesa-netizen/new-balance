export function visibleQuestions(fields,answers){
  const visible=[];
  for(const field of fields){const condition=field.showWhen;visible.push(!condition||!!visible[condition.question]&&answers[condition.question]===condition.value);}
  return visible;
}
export const canonicalAnswers=(fields,answers)=>visibleQuestions(fields,answers).map((visible,i)=>visible?answers[i]:'');
export function cleanConditions(fields,removedIndex=null){
  for(const [i,field] of fields.entries()){
    const condition=field.showWhen;if(!condition)continue;
    if(removedIndex!==null){if(condition.question===removedIndex){delete field.showWhen;continue;}if(condition.question>removedIndex)condition.question--;}
    const parent=fields[condition.question];
    if(!Number.isInteger(condition.question)||condition.question<0||condition.question>=i||parent?.type!=='choice'||!parent.options.includes(condition.value))delete field.showWhen;
  }
}
export function bindConditionalAnswers(form,fields){
  if(!form)return;
  const update=()=>{
    const data=new FormData(form),answers=fields.map((field,i)=>field.type==='multiple'?data.getAll('q'+i).join('; '):data.get('q'+i)||'');
    const visible=visibleQuestions(fields,answers);
    fields.forEach((field,i)=>{
      const group=form.querySelector(`[data-answer="${i}"]`);if(!group)return;group.hidden=!visible[i];
      group.querySelectorAll('input,textarea,select').forEach(control=>{
        control.disabled=!visible[i];
        if(!visible[i]){if(control.type==='checkbox'||control.type==='radio')control.checked=false;else control.value='';}
      });
    });
  };
  form.addEventListener('input',update);form.addEventListener('change',update);update();
}
export function mountFormConditions(root,content,{dialog,close,esc,dirty,render}){
  root.querySelectorAll('[data-question]').forEach(input=>{
    const i=+input.dataset.question,field=content.fields[i],card=input.closest('article');
    const button=document.createElement('button');button.type='button';button.textContent='Exibição da pergunta '+(i+1);
    const status=document.createElement('p');status.className='muted';status.textContent=field.showWhen?`Mostrar quando a pergunta ${field.showWhen.question+1} for “${field.showWhen.value}”.`:'Sempre visível.';
    card.append(status,button);
    button.onclick=()=>{
      const candidates=content.fields.map((f,n)=>({field:f,index:n})).filter(x=>x.index<i&&x.field.type==='choice');
      dialog(`<h2>Exibição da pergunta ${i+1}</h2><form id="question-condition"><label class="field">Mostrar quando<select name="question" aria-label="Pergunta anterior"><option value="">Sempre mostrar</option>${candidates.map(c=>`<option value="${c.index}" ${field.showWhen?.question===c.index?'selected':''}>${c.index+1}: ${esc(content.questions[c.index])}</option>`).join('')}</select></label><label class="field">Resposta que exibe esta pergunta<select name="value" aria-label="Resposta de exibição"></select></label><p>Use uma pergunta de escolha única anterior. Perguntas ocultas não são obrigatórias nem pontuadas.</p><button>Aplicar regra</button><button type="button" id="condition-cancel">Cancelar</button></form>`,()=>{
        const form=document.querySelector('#question-condition');
        const options=()=>{const parent=content.fields[+form.elements.question.value];form.elements.value.disabled=form.elements.question.value==='';form.elements.value.innerHTML=(parent?.options||[]).map(value=>`<option value="${esc(value)}" ${field.showWhen?.value===value?'selected':''}>${esc(value)}</option>`).join('');};
        form.elements.question.onchange=options;options();form.querySelector('#condition-cancel').onclick=close;
        form.onsubmit=e=>{e.preventDefault();if(form.elements.question.value==='')delete field.showWhen;else{if(!form.elements.value.value)return;field.showWhen={question:+form.elements.question.value,value:form.elements.value.value};}close();dirty();render();};
      });
    };
  });
}
