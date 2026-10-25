// Keep answer columns distinct even when questions have the same label.
export function responseTable(content,formatDate=String){
  const keys=[],names=new Map(),used=new Set(['Data']);
  const records=content.responses.map(response=>{
    const seen=new Map(),values=new Map();
    (response.questions||content.questions).forEach((q,i)=>{
      const occurrence=(seen.get(q)||0)+1;seen.set(q,occurrence);const key=JSON.stringify([q,occurrence]);
      if(!names.has(key)){let name=q||'Pergunta',n=2;while(used.has(name))name=(q||'Pergunta')+' ('+(n++)+')';used.add(name);names.set(key,name);keys.push(key);}
      values.set(key,response.answers[i]??'');
    });
    return {at:response.at,values};
  });
  return {columns:['Data',...keys.map(k=>names.get(k))],rows:records.map(r=>[formatDate(r.at),...keys.map(k=>r.values.get(k)??'')])};
}
export function recordsWorkbook(columns,rows,types=[]){
  if(!columns.length||columns.length>1024||(rows.length+1)*columns.length>50000)throw Error('A conversão aceita até 50 mil células. Exporte CSV para levar todos os registros.');
  const cellData={};
  [columns,...rows].forEach((row,r)=>row.forEach((value,c)=>{
    if(value==null||value==='')return;cellData[r]??={};
    const number=r>0&&types[c]==='number'&&Number.isFinite(Number(value));
    cellData[r][c]=number?{v:Number(value),t:2}:{v:String(value),t:1};
  }));
  return {id:'records',name:'Registros',appVersion:'1.2.0',locale:'ptBR',styles:{},sheetOrder:['records'],sheets:{records:{id:'records',name:'Registros',rowCount:Math.max(1000,rows.length+1),columnCount:Math.max(26,columns.length),cellData,defaultColumnWidth:120,defaultRowHeight:25,mergeData:[]}}};
}
export function answerError(value,field){
  if(value.length>4000)return 'Use até 4000 caracteres.';
  if(field.required&&!value.trim())return 'Preencha este campo obrigatório.';
  if(!value)return '';
  if(field.type==='choice'&&!field.options.includes(value))return 'Selecione uma opção válida.';
  if(field.type==='number'&&!Number.isFinite(Number(value)))return 'Informe um número válido.';
  if(field.type==='email'&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value))return 'Informe um e-mail válido.';
  if(field.type==='date'&&(!/^\d{4}-\d{2}-\d{2}$/.test(value)||!Number.isFinite(Date.parse(value+'T00:00:00Z'))||new Date(value+'T00:00:00Z').toISOString().slice(0,10)!==value))return 'Informe uma data válida.';
  return '';
}
export function localDateTime(value){const d=new Date(value),pad=n=>String(n).padStart(2,'0');return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;}
export const safeCsv=rows=>rows.map(row=>row.map(v=>typeof v==='string'&&/^[=+@\-\t\r]/.test(v)?"'"+v:v));
export function documentSlides(content){
  return content.text.split(/(?=^#{1,2} )/m).filter(s=>s.trim()).slice(0,100).map((section,index)=>{
    const pictures=[],lines=section.trim().split('\n').filter(line=>{const m=/^!\[[^\]]*\]\(drap-image:([a-zA-Z0-9_-]+)\)$/.exec(line.trim());if(!m)return true;const im=content.images?.find(im=>im.id===m[1]);if(im)pictures.push(im);return false;});
    const slide={title:(lines.shift()||'Slide '+(index+1)).replace(/^#+\s*/,''),body:lines.join('\n').trim(),notes:''};
    if(pictures.length)slide.objects=pictures.map((im,i)=>{const ratio=Number.isFinite(im.ratio)&&im.ratio>0?im.ratio:16/9;const h=Math.max(1,Math.min(60/pictures.length,40*16/9/ratio)),w=Math.max(1,Math.min(40,h*ratio*9/16));return {id:'image-'+i,type:'image',src:im.src,alt:im.alt||'',x:54,y:30+i*60/pictures.length,w,h};});
    return slide;
  });
}
