export const pageDefaults={size:'A4',orientation:'portrait',margin:20,font:'Arial',fontSize:12,lineHeight:1.5,align:'left',mode:'page'};
export function documentStyle(settings={}){
  const s={...pageDefaults,...settings};
  return `font-family:${s.font};font-size:${s.fontSize}pt;line-height:${s.lineHeight};text-align:${s.align};`;
}
export function printDocument(settings={}){
  const s={...pageDefaults,...settings},style=document.createElement('style');
  style.textContent=`@page{size:${s.size} ${s.orientation};margin:${s.margin}mm}`;
  document.head.append(style);try{window.print();}finally{style.remove();}
}
export function mountDocumentTools(root,content,{editor,changed,dialog,bind,close,escape:esc,readOnly}){
  const bar=document.createElement('div');bar.className='toolbar';bar.innerHTML='<button id="document-outline">Estrutura do documento</button><button id="document-statistics">Contagem detalhada</button><button id="document-page">Configurar página</button><button id="document-numbered">Lista numerada</button><button id="document-quote">Citação</button><button id="document-code">Bloco de código</button><button id="document-divider">Linha horizontal</button>';
  root.querySelector('.document').before(bar);
  const panel=document.createElement('aside');panel.className='document-outline no-print';panel.hidden=true;panel.setAttribute('aria-label','Estrutura do documento');root.querySelector('.document').before(panel);
  function refresh(){
    const preview=root.querySelector('#preview'),s={...pageDefaults,...content.page};const zoom=preview.style.zoom;preview.style.cssText=documentStyle(s);preview.style.zoom=zoom;
    preview.dataset.pageMode=s.mode;preview.style.setProperty('--document-width',s.mode==='wide'?'100%':s.orientation==='landscape'?'1120px':'800px');
    if(panel.hidden)return;
    const headings=[...preview.querySelectorAll('h1,h2,h3,h4,h5,h6')];
    panel.innerHTML='<strong>Estrutura do documento</strong>'+ (headings.length?headings.map((h,i)=>`<button data-outline="${i}" style="padding-left:${(Number(h.tagName[1])-1)*12+8}px">${esc(h.textContent||'Título sem texto')}</button>`).join(''):'<p>Adicione títulos para navegar pelo documento.</p>');
    panel.querySelectorAll('button').forEach(button=>button.onclick=()=>{const h=headings[+button.dataset.outline];h.scrollIntoView({block:'center',behavior:'smooth'});h.tabIndex=-1;h.focus({preventScroll:true});});
  }
  bind('document-outline',()=>{panel.hidden=!panel.hidden;root.querySelector('#document-outline').setAttribute('aria-expanded',String(!panel.hidden));refresh();});
  bind('document-statistics',()=>{const text=editor()?.text()??content.text,selected=editor()?.selectionText()??'',stats=t=>{const trimmed=t.trim();return [['Palavras',trimmed?trimmed.split(/\s+/u).length:0],['Caracteres',[...t].length],['Caracteres sem espaços',[...t.replace(/\s/gu,'')].length]];};dialog('<h2>Contagem detalhada</h2>'+[['Documento',text],...(selected?[['Seleção',selected]]:[])].map(([label,t])=>'<h3>'+label+'</h3><dl>'+stats(t).map(([name,n])=>'<dt>'+name+'</dt><dd>'+n.toLocaleString('pt-BR')+'</dd>').join('')+'</dl>').join('')+'<button id="statistics-close">Fechar</button>',()=>bind('statistics-close',close));});
  bind('document-page',()=>{
    if(readOnly)return;const s={...pageDefaults,...content.page};
    const select=(name,label,opts)=>`<label class="field">${label}<select name="${name}">${Object.entries(opts).map(([v,l])=>`<option value="${v}" ${String(s[name])===v?'selected':''}>${l}</option>`).join('')}</select></label>`;
    dialog(`<h2>Configurar página</h2><form id="page-form">${select('mode','Visualização',{page:'Largura de página',wide:'Largura livre'})}${select('size','Papel',{A4:'A4',Letter:'Carta'})}${select('orientation','Orientação',{portrait:'Retrato',landscape:'Paisagem'})}<label class="field">Margens de impressão (mm)<input name="margin" type="number" min="5" max="40" value="${s.margin}" required></label>${select('font','Fonte do documento',{Arial:'Arial',Georgia:'Georgia','Times New Roman':'Times New Roman','Courier New':'Courier New'})}<label class="field">Tamanho base (pt)<input name="fontSize" type="number" min="8" max="36" value="${s.fontSize}" required></label>${select('lineHeight','Espaçamento entre linhas',{'1':'Simples','1.15':'1,15','1.5':'1,5','2':'Duplo'})}${select('align','Alinhamento do documento',{left:'Esquerda',center:'Centro',right:'Direita',justify:'Justificado'})}<p>Fonte e alinhamento se aplicam ao documento inteiro. Papel e margens são usados na impressão/PDF e no DOCX; a edição permanece contínua.</p><button class="primary">Aplicar configuração</button></form>`,()=>bind('page-form',e=>{e.preventDefault();const s=Object.fromEntries(new FormData(e.target));for(const k of ['margin','fontSize','lineHeight'])s[k]=Number(s[k]);content.page={...content.page,...s};refresh();changed();close();},'submit'));
  });
  for(const [id,command] of [['numbered','ordered'],['quote','quote'],['code','code'],['divider','divider']]){bind('document-'+id,()=>{if(!readOnly)editor()?.format(command);});root.querySelector('#document-'+id).disabled=readOnly;}
  root.querySelector('#document-page').disabled=readOnly;
  refresh();return {refresh};
}
