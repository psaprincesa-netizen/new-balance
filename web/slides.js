import {openPresenter} from './presenter.js';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const slideStyle=s=>`background:${/^#[a-f0-9]{6}$/i.test(s.background||'')?s.background:''};color:${/^#[a-f0-9]{6}$/i.test(s.foreground||'')?s.foreground:''};`;
const bounds=o=>`left:${o.x}%;top:${o.y}%;width:${o.w}%;height:${o.h}%;transform:rotate(${o.rotation||0}deg);`;
export function slideMarkup(slide,{editable=false,selected=null,heading='h2'}={}){
  return `<${heading} class="slide-heading">${esc(slide.title)}</${heading}><p class="slide-body ${slide.objects?.length?'with-objects':''}">${esc(slide.body)}</p>`+(slide.objects||[]).map(o=>`<div class="slide-object ${o.type} ${selected===o.id?'selected':''}" data-object="${esc(o.id)}" style="${bounds(o)}${o.type!=='image'?`color:${esc(o.color||'#172018')};background:${o.type==='text'?'transparent':esc(o.fill||'#4b5320')};font-size:${(o.fontSize||24)/9.6}cqw;font-weight:${o.bold?'bold':'normal'};text-align:${esc(o.align||'left')};`:''}" ${editable?'tabindex="0" role="button" aria-label="Selecionar objeto '+esc(o.alt||o.text||o.type)+'"':''}>${o.type==='image'?`<img src="${esc(o.src)}" alt="${esc(o.alt||'Imagem do slide')}" draggable="false">`:`<span>${esc(o.text||'')}</span>`}${editable&&selected===o.id?'<button class="slide-resize" aria-label="Redimensionar objeto" title="Arraste para redimensionar">↘</button>':''}</div>`).join('');
}
export async function raster(file){
  if(!['image/png','image/jpeg','image/webp'].includes(file.type))throw Error('Escolha uma imagem PNG, JPEG ou WebP.');
  if(file.size>12000000)throw Error('A imagem original deve ter até 12 MB.');
  const bitmap=await createImageBitmap(file);
  try{
    if(bitmap.width*bitmap.height>40000000)throw Error('A imagem deve ter até 40 megapixels.');
    const canvas=document.createElement('canvas');let scale=Math.min(1,1200/Math.max(bitmap.width,bitmap.height)),src;
    do{canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);src=canvas.toDataURL('image/png');scale*=.8;}while(src.length>400000&&Math.min(canvas.width,canvas.height)>100);
    if(src.length>400000)throw Error('Não foi possível otimizar a imagem para este arquivo.');
    return {src,ratio:bitmap.width/bitmap.height};
  }finally{bitmap.close();}
}
export function mountSlides(root,content,{dirty,notify,present,readOnly=false,initialIndex=0,onSelect=()=>{}}){
  let index=Math.max(0,Math.min(initialIndex,content.slides.length-1)),selected=null,past=[],future=[];
  const current=()=>content.slides[index];
  const snapshot=()=>JSON.stringify(content);
  function checkpoint(){past.push(snapshot());if(past.length>12)past.shift();future.length=0;}
  function changed(){dirty();render();}
  function change(fn){if(readOnly)return;checkpoint();fn();changed();}
  function add(obj){
    if((current().objects||[]).length>=30)return notify('Até 30 objetos por slide.');
    if(snapshot().length+JSON.stringify(obj).length>1800000)return notify('Esta apresentação atingiu o limite de imagens. Crie outro arquivo para continuar.');
    change(()=>{obj.id=crypto.randomUUID();(current().objects??=[]).push(obj);selected=obj.id;});
  }
  function render(){
    onSelect(index);
    const s=current(),o=s.objects?.find(o=>o.id===selected);
    root.innerHTML=`<div class="toolbar"><button id="add-slide">＋ Slide</button><button id="duplicate-slide">Duplicar slide</button><button id="remove-slide">Excluir slide</button><button id="prev-slide">Mover antes</button><button id="after-slide">Mover depois</button><button id="slide-undo" ${past.length?'':'disabled'}>Desfazer alteração</button><button id="slide-redo" ${future.length?'':'disabled'}>Refazer alteração</button><label>Tema<select id="slide-theme" aria-label="Tema dos slides">${Object.entries({light:'Claro',army:'Verde-exército',navy:'Azul-escuro'}).map(([v,l])=>`<option value="${v}" ${v===(content.theme||'light')?'selected':''}>${l}</option>`).join('')}</select></label><button id="present" class="primary">▷ Apresentar</button><button id="present-separate">Console do apresentador</button></div><div class="toolbar"><button id="slide-image">Inserir imagem</button><button id="slide-text">Caixa de texto</button><button id="slide-rect">Retângulo</button><button id="slide-ellipse">Elipse</button><button id="slide-layout">Inserir layout de duas colunas</button><button id="slide-master">Usar estilo nos novos slides</button><span class="muted">Selecione um objeto para editar. Arraste para mover; use a alça ↘ para redimensionar.</span></div><div class="slides-workspace"><nav class="slide-list" aria-label="Slides">${content.slides.map((s,i)=>`<button data-slide="${i}" aria-current="${i===index?'true':'false'}" class="${i===index?'primary':''}">${i+1}. ${esc(s.title||'Sem título')}<small>${s.objects?.length||0} objetos${s.hidden?' · Oculto':''}</small></button>`).join('')}</nav><div class="slide-main"><div class="slide-stage" id="slide-preview" data-theme="${esc(content.theme||'light')}" style="${slideStyle(s)}">${slideMarkup(s,{editable:!readOnly,selected})}</div><div class="slide-properties"><label class="field">Selecionar vários objetos<select id="slide-multiple" multiple size="3" aria-label="Selecionar vários objetos">${(s.objects||[]).map(obj=>`<option value="${esc(obj.id)}">${esc(obj.text||obj.alt||obj.type)}</option>`).join('')}</select></label><div class="toolbar"><button id="slide-group">Agrupar selecionados</button><button id="slide-ungroup">Desagrupar objeto</button></div><label class="field">Selecionar objeto / camada<select id="slide-object-list" aria-label="Selecionar objeto ou camada"><option value="">Nenhum</option>${(s.objects||[]).map((obj,i)=>`<option value="${esc(obj.id)}" ${selected===obj.id?'selected':''}>${i+1}. ${esc(obj.alt||obj.text||({image:'Imagem',text:'Texto',rect:'Retângulo',ellipse:'Elipse'}[obj.type]))}</option>`).join('')}</select></label>${o?`<fieldset><legend>Objeto selecionado</legend><label>Rotação (graus)<input id="object-rotation" type="number" min="-360" max="360" value="${o.rotation||0}" aria-label="Rotação do objeto"></label>${o.type==='image'?`<label class="field">Descrição da imagem<input id="object-alt" maxlength="200" value="${esc(o.alt||'')}"></label>`:`<label class="field">Texto do objeto<textarea aria-label="Texto do objeto" id="object-text" maxlength="10000">${esc(o.text||'')}</textarea></label><div class="toolbar"><label>Tamanho<input id="object-fontSize" type="number" min="8" max="96" value="${o.fontSize||24}" aria-label="Tamanho do texto"></label><label>Cor do texto<input id="object-color" type="color" value="${o.color||'#172018'}"></label>${o.type!=='text'?`<label>Preenchimento<input id="object-fill" type="color" value="${o.fill||'#4b5320'}"></label>`:''}<label><input id="object-bold" type="checkbox" ${o.bold?'checked':''}> Negrito</label><label>Alinhamento<select id="object-align" aria-label="Alinhamento do objeto">${['left','center','right'].map((v,i)=>`<option value="${v}" ${(o.align||'left')===v?'selected':''}>${['Esquerda','Centro','Direita'][i]}</option>`).join('')}</select></label></div>`}<div class="toolbar">${[['x','Posição horizontal'],['y','Posição vertical'],['w','Largura'],['h','Altura']].map(([k,l])=>`<label>${l} (%)<input id="object-${k}" aria-label="${l} do objeto" type="number" min="${k==='w'||k==='h'?1:0}" max="100" step="0.1" value="${+o[k].toFixed(1)}"></label>`).join('')}</div><div class="toolbar"><label>Alinhar na página<select id="object-position"><option value="">Escolher…</option><option value="left">Esquerda</option><option value="center">Centro horizontal</option><option value="right">Direita</option><option value="top">Topo</option><option value="middle">Centro vertical</option><option value="bottom">Base</option></select></label><button id="object-distribute-x">Distribuir todos horizontalmente</button><button id="object-distribute-y">Distribuir todos verticalmente</button><button id="object-front">Trazer à frente</button><button id="object-back">Enviar para trás</button><button id="object-copy">Duplicar objeto</button><button id="object-delete">Excluir objeto</button></div></fieldset>`:'<p class="muted">Insira uma imagem, texto ou forma usando os botões acima.</p>'}<fieldset><legend>Configuração do slide</legend><div class="toolbar"><label><input id="slide-hidden" type="checkbox" ${s.hidden?'checked':''}> Ocultar na apresentação</label><label>Fundo<input id="slide-background" type="color" value="${s.background||(content.theme==='army'?'#4b5320':content.theme==='navy'?'#102237':'#ffffff')}"></label><label>Cor do título e conteúdo<input id="slide-foreground" type="color" value="${s.foreground||(!content.theme||content.theme==='light'?'#172018':'#ffffff')}"></label><button id="slide-reset-colors">Usar cores do tema</button><label>Transição<select id="slide-transition">${Object.entries({none:'Nenhuma',fade:'Dissolver',push:'Deslizar'}).map(([v,l])=>`<option value="${v}" ${(s.transition||'none')===v?'selected':''}>${l}</option>`).join('')}</select></label><button id="slide-apply-style">Aplicar fundo e transição a todos</button></div></fieldset><label class="field">Título<input id="slide-title" value="${esc(s.title)}"></label><label class="field">Conteúdo<textarea id="slide-body" rows="4">${esc(s.body)}</textarea></label><label class="field">Notas do apresentador<textarea id="slide-notes" rows="3">${esc(s.notes)}</textarea></label></div></div></div>`;
    const bind=(id,fn,event='click')=>{const el=root.querySelector('#'+id);if(el)el.addEventListener(event,fn);};
    root.querySelectorAll('[data-slide]').forEach(el=>el.onclick=()=>{index=+el.dataset.slide;selected=null;render();});
    bind('slide-object-list',e=>{selected=e.target.value||null;render();},'change');
    bind('present',()=>present(content.slides,content.theme||'light'));
    bind('present-separate',()=>openPresenter(content,'DRAP office',notify));
    if(readOnly){root.querySelectorAll('input,textarea,select,button:not([data-slide]):not(#present):not(#present-separate)').forEach(el=>el.disabled=true);return;}
    bind('slide-group',()=>{const ids=[...root.querySelector('#slide-multiple').selectedOptions].map(option=>option.value);if(ids.length<2)return notify('Selecione pelo menos dois objetos.');change(()=>{const group=crypto.randomUUID();for(const obj of s.objects)if(ids.includes(obj.id))obj.group=group;selected=ids[0];});});
    bind('slide-ungroup',()=>{if(!o?.group)return notify('Selecione um objeto agrupado.');change(()=>{const group=o.group;for(const obj of s.objects)if(obj.group===group)delete obj.group;});});
    bind('slide-master',()=>change(()=>{content.master={};for(const key of ['background','foreground','transition'])if(s[key]!==undefined)content.master[key]=s[key];notify('O estilo será aplicado aos novos slides.');}));
    bind('slide-layout',()=>{if((s.objects||[]).length>28)return notify('O layout precisa de espaço para dois objetos.');change(()=>{s.objects??=[];for(const [x,text] of [[7,'Primeira coluna'],[53,'Segunda coluna']])s.objects.push({id:crypto.randomUUID(),type:'text',x,y:34,w:40,h:54,text,fontSize:24,color:s.foreground||'#172018',align:'left',bold:false});});});
    for(const key of ['title','body','notes']){
      bind('slide-'+key,()=>{checkpoint();root.querySelector('#slide-undo').disabled=false;root.querySelector('#slide-redo').disabled=true;},'focus');
      bind('slide-'+key,e=>{s[key]=e.target.value;dirty();const preview=root.querySelector('#slide-preview');if(key!=='notes')preview.querySelector(key==='title'?'.slide-heading':'.slide-body').textContent=e.target.value;if(key==='title')root.querySelector(`[data-slide="${index}"]`).firstChild.textContent=(index+1)+'. '+(s.title||'Sem título');},'input');
    }
    for(const key of ['background','foreground','transition','hidden'])bind('slide-'+key,e=>change(()=>s[key]=key==='hidden'?e.target.checked:e.target.value),'change');
    bind('slide-reset-colors',()=>change(()=>{delete s.background;delete s.foreground;}));
    bind('slide-apply-style',()=>change(()=>{for(const entry of content.slides)for(const key of ['background','foreground','transition']){if(s[key]===undefined)delete entry[key];else entry[key]=s[key];}}));
    bind('slide-theme',e=>change(()=>content.theme=e.target.value),'change');
    bind('add-slide',()=>{if(content.slides.length>=100)return notify('Até 100 slides por arquivo.');change(()=>{content.slides.splice(index+1,0,{title:'Novo slide',body:'',notes:'',...content.master});index++;selected=null;});});
    bind('duplicate-slide',()=>{if(content.slides.length>=100||snapshot().length+JSON.stringify(s).length>1800000)return notify('Limite da apresentação atingido.');change(()=>{content.slides.splice(index+1,0,structuredClone(s));index++;selected=null;});});
    bind('remove-slide',()=>{if(content.slides.length===1)return notify('Mantenha pelo menos um slide.');change(()=>{content.slides.splice(index,1);index=Math.min(index,content.slides.length-1);selected=null;});});
    for(const [id,delta] of [['prev-slide',-1],['after-slide',1]])bind(id,()=>{if(!content.slides[index+delta])return;change(()=>{[content.slides[index],content.slides[index+delta]]=[content.slides[index+delta],content.slides[index]];index+=delta;});});
    for(const [id,from,to] of [['slide-undo',past,future],['slide-redo',future,past]])bind(id,()=>{if(!from.length)return;to.push(snapshot());const restored=JSON.parse(from.pop()),attachments=content.attachments;for(const k of Object.keys(content))delete content[k];Object.assign(content,restored);if(attachments!==undefined)content.attachments=attachments;else delete content.attachments;index=Math.min(index,content.slides.length-1);selected=null;changed();});
    bind('slide-image',()=>{
      const input=document.createElement('input');input.type='file';input.accept='image/png,image/jpeg,image/webp';
      const target=s;
      input.onchange=async()=>{if(!input.files[0])return;try{notify('Preparando imagem…');const {src,ratio}=await raster(input.files[0]);if(!root.isConnected||current()!==target)return;let w=40,h=w*16/9/ratio;if(h>60){h=60;w=h*ratio*9/16;}add({type:'image',src,alt:input.files[0].name.slice(0,200),x:54,y:30,w:Math.max(1,w),h:Math.max(1,h)});}catch(e){notify(e.message);}};input.click();
    });
    for(const type of ['text','rect','ellipse'])bind('slide-'+type,()=>add({type,x:54,y:32,w:36,h:type==='text'?20:35,text:type==='text'?'Digite seu texto':'',fontSize:24,color:type==='text'&&(!content.theme||content.theme==='light')?'#172018':'#ffffff',fill:'#4b5320',align:'left',bold:false}));
    if(o){
      for(const k of ['rotation','alt','text','fontSize','color','fill','bold','align','x','y','w','h'])bind('object-'+k,e=>{
        let value=k==='bold'?e.target.checked:['rotation','fontSize','x','y','w','h'].includes(k)?Number(e.target.value):e.target.value;
        if(typeof value==='number'&&!Number.isFinite(value))return;
        if(['x','y','w','h'].includes(k))value=Math.max(k==='w'||k==='h'?1:0,Math.min(k==='x'?100-o.w:k==='y'?100-o.h:k==='w'?100-o.x:100-o.y,value));
        if(k==='rotation')value=Math.max(-360,Math.min(360,value));
        if(k==='fontSize')value=Math.max(8,Math.min(96,value));
        checkpoint();o[k]=value;dirty();e.target.value=k==='bold'?e.target.value:value;const el=root.querySelector(`[data-object="${CSS.escape(o.id)}"]`);el.style.transform='rotate('+(o.rotation||0)+'deg)';el.style.left=o.x+'%';el.style.top=o.y+'%';el.style.width=o.w+'%';el.style.height=o.h+'%';if(o.type==='image')el.querySelector('img').alt=o.alt||'Imagem do slide';else{el.querySelector('span').textContent=o.text||'';el.style.color=o.color||'#172018';el.style.background=o.type==='text'?'transparent':o.fill||'#4b5320';el.style.fontSize=(o.fontSize||24)/9.6+'cqw';el.style.fontWeight=o.bold?'bold':'normal';el.style.textAlign=o.align||'left';}root.querySelector('#slide-undo').disabled=false;root.querySelector('#slide-redo').disabled=true;
      },'change');
      bind('object-position',e=>change(()=>{const v=e.target.value;if(['left','center','right'].includes(v))o.x=v==='left'?0:v==='center'?(100-o.w)/2:100-o.w;else if(['top','middle','bottom'].includes(v))o.y=v==='top'?0:v==='middle'?(100-o.h)/2:100-o.h;}),'change');
      for(const axis of ['x','y'])bind('object-distribute-'+axis,()=>{const objects=[...s.objects].sort((a,b)=>a[axis]-b[axis]),size=axis==='x'?'w':'h';if(objects.length<3)return notify('Insira pelo menos três objetos para distribuir.');const first=objects[0][axis],last=objects.at(-1)[axis]+objects.at(-1)[size],total=objects.reduce((n,o)=>n+o[size],0),gap=(last-first-total)/(objects.length-1);if(gap<0)return notify('Afaste os objetos das extremidades para distribuir sem sobreposição.');change(()=>{let cursor=first;for(const obj of objects){obj[axis]=cursor;cursor+=obj[size]+gap;}});});
      bind('object-delete',()=>change(()=>{s.objects=s.objects.filter(n=>n!==o);selected=null;}));
      bind('object-copy',()=>{const copy=structuredClone(o);delete copy.group;add(copy);});
      bind('object-front',()=>change(()=>{s.objects=s.objects.filter(n=>n!==o);s.objects.push(o);}));
      bind('object-back',()=>change(()=>{s.objects=s.objects.filter(n=>n!==o);s.objects.unshift(o);}));
    }
    root.querySelectorAll('[data-object]').forEach(el=>{
      el.onclick=()=>{if(selected!==el.dataset.object){selected=el.dataset.object;render();}};
      el.onkeydown=e=>{
        if(['Enter',' '].includes(e.key)){e.preventDefault();selected=el.dataset.object;render();return;}
        const shifts={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};
        if(shifts[e.key]){e.preventDefault();const obj=s.objects.find(o=>o.id===el.dataset.object),[dx,dy]=shifts[e.key],step=e.shiftKey?5:1;change(()=>{selected=obj.id;const group=obj.group?s.objects.filter(entry=>entry.group===obj.group):[obj],moveX=Math.max(-Math.min(...group.map(p=>p.x)),Math.min(100-Math.max(...group.map(p=>p.x+p.w)),dx*step)),moveY=Math.max(-Math.min(...group.map(p=>p.y)),Math.min(100-Math.max(...group.map(p=>p.y+p.h)),dy*step));for(const member of group){member.x+=moveX;member.y+=moveY;}});root.querySelector(`[data-object="${CSS.escape(obj.id)}"]`).focus();}
      };
      el.onpointerdown=e=>{
        if(e.button!==0)return;e.preventDefault();const obj=s.objects.find(o=>o.id===el.dataset.object),resize=!!e.target.closest('.slide-resize');
        const group=obj.group?s.objects.filter(entry=>entry.group===obj.group):[obj],origins=group.map(entry=>({entry,x:entry.x,y:entry.y}));
        const box=root.querySelector('#slide-preview').getBoundingClientRect(),start={x:e.clientX,y:e.clientY,...Object.fromEntries(['x','y','w','h'].map(k=>['o'+k,obj[k]]))};
        selected=obj.id;el.setPointerCapture(e.pointerId);let moved=false;
        el.onpointermove=ev=>{const dx=(ev.clientX-start.x)/box.width*100,dy=(ev.clientY-start.y)/box.height*100;if(!moved&&Math.abs(dx)+Math.abs(dy)<.4)return;if(!moved){checkpoint();moved=true;}
          if(resize){const factor=Math.max(1/start.ow,1/start.oh,Math.min((start.ow+dx)/start.ow,(100-obj.x)/start.ow,(100-obj.y)/start.oh));if(obj.type==='image'){obj.w=start.ow*factor;obj.h=start.oh*factor;}else{obj.w=Math.max(1,Math.min(100-obj.x,start.ow+dx));obj.h=Math.max(1,Math.min(100-obj.y,start.oh+dy));}}
          else{const moveX=Math.max(-Math.min(...origins.map(p=>p.x)),Math.min(100-Math.max(...origins.map(p=>p.x+p.entry.w)),dx)),moveY=Math.max(-Math.min(...origins.map(p=>p.y)),Math.min(100-Math.max(...origins.map(p=>p.y+p.entry.h)),dy));for(const p of origins){p.entry.x=p.x+moveX;p.entry.y=p.y+moveY;root.querySelector(`[data-object="${CSS.escape(p.entry.id)}"]`).style.cssText+=bounds(p.entry);}}el.style.cssText+=bounds(obj);
        };
        const finish=()=>{el.onpointermove=null;el.onpointerup=null;el.onpointercancel=null;if(moved)dirty();render();};el.onpointerup=finish;el.onpointercancel=finish;
      };
    });
  }
  render();
}
export function printSlides(content){
  const deck=document.createElement('div');deck.className='print-slide-deck';deck.innerHTML=content.slides.map(s=>`<section class="slide-stage" data-theme="${esc(content.theme||'light')}" style="${slideStyle(s)}">${slideMarkup(s)}</section>`).join('');
  const style=document.createElement('style');style.textContent='@page{size:A4 landscape;margin:10mm}';
  document.head.append(style);document.body.append(deck);document.body.classList.add('printing-slides');
  try{window.print();}finally{deck.remove();style.remove();document.body.classList.remove('printing-slides');}
}
