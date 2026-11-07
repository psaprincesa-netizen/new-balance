export async function mountAssistant(root, {api, esc, notify, items, saveDocument}) {
  root.innerHTML = '<p role="status">Verificando conexão com Gemini…</p>';
  let config;
  try {config = await api('/api/ai/status');} catch(error) {root.textContent=error.message;return;}
  if(!root.isConnected)return;
  root.innerHTML = `<p class="muted">Gere textos, resuma ou analise um arquivo salvo. Somente o arquivo selecionado é enviado. Imagens, anexos e gabaritos de formulários não são enviados. Arquivos extensos usam um trecho ou amostra; alterações ainda não salvas ficam de fora.</p>
    ${!config.configured?'<p class="error" role="status">O Gemini ainda precisa de autenticação no servidor. O administrador deve configurar o AI Gateway.</p>':''}
    <form id="ai-request"><label class="field">Ação do Gemini<select name="action"><option value="generate">Gerar texto</option><option value="summarize">Resumir arquivo</option><option value="analyze">Analisar arquivo</option></select></label>
    <label class="field">Arquivo salvo para contexto<select name="item_id"><option value="">Sem arquivo</option>${items.filter(i=>!i.deleted).map(i=>`<option value="${esc(i.id)}">${esc(i.title)}</option>`).join('')}</select></label>
    <label class="field">Instruções para o Gemini<textarea name="prompt" rows="5" maxlength="4000" placeholder="Ex.: prepare um plano de lançamento com tarefas e riscos." required></textarea></label>
    <label class="checklist"><input name="consent" type="checkbox" required>Enviar este pedido e o conteúdo selecionado ao Google Gemini via Vercel. Os pedidos podem consumir créditos de IA.</label>
    <button class="primary" ${config.configured?'':'disabled'}>Executar com Gemini</button></form>
    <p id="ai-status" role="status" aria-live="polite"></p>
    <section id="ai-result" hidden><h2>Resultado do Gemini</h2><p>Confira os fatos e cálculos antes de usar o resultado. O arquivo original permanece preservado.</p><label class="field">Texto gerado<textarea id="ai-text" rows="15" readonly></textarea></label><button id="ai-copy">Copiar resultado</button><button id="ai-save">Salvar como novo documento</button></section>`;
  const form=root.querySelector('form'), status=root.querySelector('#ai-status'), output=root.querySelector('#ai-text');
  form.elements.action.onchange=()=>{form.elements.prompt.required=form.elements.action.value==='generate';form.elements.item_id.required=form.elements.action.value!=='generate';};
  form.onsubmit=async event=>{
    event.preventDefault();const button=form.querySelector('button');button.disabled=true;
    root.querySelector('#ai-result').hidden=true;output.value='';status.textContent='Aguardando o Gemini…';
    const data=Object.fromEntries(new FormData(form));data.consent=form.elements.consent.checked;data.item_id=data.item_id||null;
    try {
      const result=await api('/api/ai',data);if(!root.isConnected)return;
      output.value=result.text;root.querySelector('#ai-result').hidden=false;
      status.textContent='Resposta recebida do Google Gemini.'+(result.contextTruncated?' A análise usou apenas um trecho/amostra do arquivo.':'')+(result.outputTruncated?' O resultado atingiu o limite de tamanho; peça uma continuação mais específica.':'');
    } catch(error){if(root.isConnected)status.textContent=error.message;}
    finally {button.disabled=!config.configured;}
  };
  root.querySelector('#ai-copy').onclick=async()=>{try{await navigator.clipboard.writeText(output.value);notify('Resultado copiado.');}catch{notify('Selecione o texto do resultado e copie pelo teclado.');}};
  root.querySelector('#ai-save').onclick=async event=>{
    if(!output.value)return;const button=event.currentTarget;button.disabled=true;
    try {await saveDocument(output.value);}catch(error){notify(error.message);button.disabled=false;}
  };
}
