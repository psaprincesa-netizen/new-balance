const MAX_FILE_BYTES=1000000,MAX_ATTACHMENTS=20;
export const safeName=name=>String(name).replace(/[\x00-\x1f\x7f/\\]/g,'_').trim().slice(0,200)||'Arquivo';
export function assertContentCapacity(content){
  // Reserve space for JSON separators used by the server's ASCII size check.
  const serialized=JSON.stringify(content).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
  if(serialized.length>1800000)throw Error('Este conteúdo excede o espaço disponível. Remova anexos/imagens ou use um vínculo para outro arquivo.');
}
export function prepareDocumentInsertion(source,destination,idFactory=()=>crypto.randomUUID()){
  const images=(source.images||[]).map(image=>({...image,id:idFactory()}));
  if((destination.images||[]).length+images.length>20)throw Error('O documento aceita até 20 imagens.');
  const ids=new Map((source.images||[]).map((image,i)=>[image.id,images[i].id]));
  const text=source.text.replace(/\]\(drap-image:([a-zA-Z0-9_-]+)\)/g,(match,id)=>ids.has(id)?'](drap-image:'+ids.get(id)+')':match);
  assertContentCapacity({...destination,text:(destination.text||'')+'\n'+text,images:[...(destination.images||[]),...images]});
  const rich=source.rich?structuredClone(source.rich):null;
  const remap=node=>{if(node.type==='image'&&node.attrs?.src){const old=node.attrs.src.replace('drap-image:','');if(ids.has(old))node.attrs.src='drap-image:'+ids.get(old);}if(node.type==='footnote')node.attrs.id=idFactory();for(const child of node.content||[])remap(child);};
  if(rich)remap(rich);
  return {text,images,...(rich?{rich}:{})};
}
export function literalMarkdown(text){return text.replace(/([\\`*_{}\[\]()#+.!|><&~-])/g,'\\$1');}
const base64=file=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Não foi possível ler o arquivo.'));reader.readAsDataURL(file);});
const fileSize=n=>n<1000?n+' B':n<1000000?(n/1000).toLocaleString('pt-BR',{maximumFractionDigits:1})+' KB':(n/1000000).toLocaleString('pt-BR',{maximumFractionDigits:1})+' MB';
export function mountInsertMenu(panel,item,{dialog,close,bind,escape:esc,notify,dirty,api,download,items,openItem,insertDocument,flush=async()=>{}}){
  const content=item.content,readOnly=item.role==='read',button=document.querySelector('#aux-insert');
  const active=()=>panel.isConnected&&document.querySelector('#aux-insert')===button;
  function add(entries){
    if(!active()||readOnly)return false;
    const attachments=[...(content.attachments||[]),...entries];
    if(attachments.length>MAX_ATTACHMENTS)throw Error('Limite de 20 anexos ou vínculos por arquivo.');
    assertContentCapacity({...content,attachments});content.attachments=attachments;dirty();render();return true;
  }
  function render(){
    const entries=content.attachments||[];panel.hidden=!entries.length;
    panel.innerHTML='<h2>Anexos e vínculos</h2><p class="muted">Anexos são incluídos no arquivo DRAP e na exportação JSON. Arquivos Office não incluem esta lista. Vínculos da biblioteca exigem acesso ao arquivo de origem.</p><div class="attachment-list">'+entries.map((entry,i)=>`<article class="attachment-card"><div><strong>${esc(entry.name)}</strong><small>${entry.kind==='file'?fileSize(entry.size):entry.kind==='item'?'Arquivo da biblioteca':'Link externo'}</small></div>${entry.kind==='link'?`<a href="${esc(entry.url)}" target="_blank" rel="noopener noreferrer">Abrir link</a>`:`<button data-attachment-open="${i}">${entry.kind==='file'?'Baixar':'Abrir arquivo'}</button>`}${!readOnly?`<button data-attachment-remove="${i}" aria-label="Remover ${esc(entry.name)}">Remover</button>`:''}</article>`).join('')+'</div>';
    panel.querySelectorAll('[data-attachment-open]').forEach(el=>el.onclick=()=>{
      const entry=entries[+el.dataset.attachmentOpen];
      if(entry.kind==='item'){openItem(entry.itemId);return;}
      try{const bytes=Uint8Array.from(atob(entry.data),c=>c.charCodeAt(0));download(entry.name,bytes,'application/octet-stream');}catch{notify('Não foi possível baixar este anexo.');}
    });
    panel.querySelectorAll('[data-attachment-remove]').forEach(el=>el.onclick=()=>{if(readOnly)return;content.attachments.splice(+el.dataset.attachmentRemove,1);dirty();render();});
  }
  function chooseFiles({accept='',multiple=false,load}){
    const input=document.createElement('input');input.type='file';input.accept=accept;input.multiple=multiple;
    input.onchange=async()=>{if(!input.files.length||!active())return;try{await flush();await load([...input.files]);}catch(e){if(active())notify(e.message);}};input.click();
  }
  function library(){
    const available=items().filter(entry=>!entry.deleted&&entry.id!==item.id);
    dialog(`<h2>Inserir da biblioteca</h2><form id="insert-library-form"><label class="field">Buscar arquivo<input id="insert-library-search" type="search"></label><label class="field">Arquivo<select name="item" id="insert-library-item" required>${available.map(entry=>`<option value="${esc(entry.id)}">${esc(entry.title)}</option>`).join('')}</select></label>${insertDocument?'<label class="field">Como inserir<select name="mode"><option value="link">Vínculo para o arquivo original</option><option value="content">Copiar conteúdo de documento ou nota</option></select></label>':''}<p>Vínculos não concedem acesso ao original. Conteúdo copiado passa a fazer parte deste arquivo.</p><p id="insert-library-error" role="alert"></p><button class="primary" ${available.length?'':'disabled'}>Inserir selecionado</button><button type="button" id="insert-cancel">Cancelar</button></form>`,()=>{
      bind('insert-cancel',close);
      bind('insert-library-search',e=>{const filtered=available.filter(entry=>entry.title.toLocaleLowerCase('pt-BR').includes(e.target.value.toLocaleLowerCase('pt-BR')));document.querySelector('#insert-library-item').innerHTML=filtered.map(entry=>`<option value="${esc(entry.id)}">${esc(entry.title)}</option>`).join('');},'input');
      bind('insert-library-form',async e=>{e.preventDefault();const submit=e.target.querySelector('button');submit.disabled=true;try{await flush();const form=new FormData(e.target),source=await api('/api/items/'+form.get('item'));if(source.deleted)throw Error('Este arquivo está na lixeira.');if(!active())return;
        if(form.get('mode')==='content'){if(!['document','note'].includes(source.kind))throw Error('Selecione um documento ou nota para copiar conteúdo.');insertDocument(source.content);}
        else add([{id:crypto.randomUUID(),kind:'item',name:safeName(source.title),itemId:source.id}]);close();notify('Conteúdo inserido. Salve para guardar a alteração.');
      }catch(err){const target=document.querySelector('#insert-library-error');if(target)target.textContent=err.message;}finally{submit.disabled=false;}},'submit');
    });
  }
  bind('aux-insert',()=>{
    if(readOnly||!active())return;
    const imageId=['document','note'].includes(item.kind)?'document-image':item.kind==='slides'?'slide-image':null;
    dialog(`<h2>Inserir</h2><div class="insert-options">${insertDocument?'<button id="insert-document-file"><strong>Documento</strong><small>Inserir conteúdo de DOCX, TXT ou Markdown</small></button>':''}<button id="insert-attachment"><strong>Arquivo / outros</strong><small>Anexar PDF, Office, ZIP, áudio ou outro arquivo · até 1 MB por arquivo</small></button><button id="insert-library"><strong>Da biblioteca</strong><small>Vincular um arquivo existente${insertDocument?' ou copiar um documento':''}</small></button>${imageId?'<button id="insert-menu-image"><strong>Imagem</strong><small>Inserir PNG, JPEG ou WebP</small></button>':''}<button id="insert-menu-link"><strong>Link</strong><small>Adicionar um endereço da web</small></button>${insertDocument?'<button id="insert-menu-table"><strong>Tabela</strong><small>Inserir uma tabela editável no texto</small></button>':''}</div><button id="insert-close">Fechar</button>`,()=>{
      bind('insert-close',close);
      bind('insert-library',library);
      bind('insert-menu-image',()=>{close();document.getElementById(imageId)?.click();});
      bind('insert-menu-table',()=>{close();document.getElementById('insert-table')?.click();});
      bind('insert-menu-link',()=>dialog('<h2>Inserir link</h2><form id="insert-url-form"><label class="field">Nome<input name="name" maxlength="200" required></label><label class="field">Endereço<input name="url" type="url" required placeholder="https://"></label><p id="insert-url-error" role="alert"></p><button class="primary">Adicionar link</button><button id="insert-url-cancel" type="button">Cancelar</button></form>',()=>{
        bind('insert-url-cancel',close);bind('insert-url-form',async e=>{e.preventDefault();try{await flush();const f=new FormData(e.target),url=new URL(f.get('url'));if(!['https:','http:'].includes(url.protocol)||url.username||url.password||url.href.length>2048)throw Error('Informe um endereço HTTP ou HTTPS válido, sem usuário ou senha.');add([{id:crypto.randomUUID(),kind:'link',name:safeName(f.get('name')),url:url.href}]);close();}catch(err){const target=document.querySelector('#insert-url-error');if(target)target.textContent=err.message;}},'submit');
      }));
      bind('insert-attachment',()=>{close();chooseFiles({multiple:true,load:async files=>{
        if(files.length+(content.attachments||[]).length>MAX_ATTACHMENTS)throw Error('Limite de 20 anexos ou vínculos por arquivo.');
        if(files.some(file=>file.size>MAX_FILE_BYTES))throw Error('Cada anexo deve ter no máximo 1 MB.');
        const estimated=files.reduce((size,file)=>size+4*Math.ceil(file.size/3),JSON.stringify(content).length);if(estimated>1800000)throw Error('Os anexos excedem o espaço disponível neste arquivo. Insira menos arquivos ou use a biblioteca.');
        const entries=[];for(const file of files)entries.push({id:crypto.randomUUID(),kind:'file',name:safeName(file.name),size:file.size,data:await base64(file)});
        if(add(entries))notify('Arquivo anexado. Salve para guardar a alteração.');
      }});});
      bind('insert-document-file',()=>{close();chooseFiles({accept:'.docx,.txt,.md,.markdown',load:async([file])=>{
        if(file.size>2500000)throw Error('O documento de origem deve ter até 2,5 MB.');
        const ext=file.name.split('.').pop().toLowerCase();let source,warnings=[];
        if(ext==='docx'){const result=await api('/api/import/preview',{name:file.name,data:await base64(file)});source=result.content;warnings=result.warnings;}
        else if(['txt','md','markdown'].includes(ext)){let text;try{text=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());}catch{throw Error('Salve o documento como texto UTF-8 para inserir.');}if(text.includes('\0'))throw Error('Este arquivo não é um documento de texto.');source={text:ext==='txt'?literalMarkdown(text):text};}
        else throw Error('Escolha DOCX, TXT ou Markdown. Para outros formatos, use Arquivo / outros.');
        if(!active())return;insertDocument(source);notify('Documento inserido na posição do cursor. Salve para guardar a alteração.');
        if(warnings.length)dialog('<h2>Documento inserido</h2>'+warnings.map(w=>'<p>'+esc(w)+'</p>').join('')+'<button id="insert-document-done">Continuar edição</button>',()=>bind('insert-document-done',close));
      }});});
    });
  });
  render();return {render};
}
