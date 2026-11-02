// Small SVG charts of live worksheet ranges. No remote renderer or scripts.
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const palette=['#4b5320','#789048','#a7b77e','#314d44','#6c8f85','#b29c68','#535d77','#ad795c'];
export function chartData(rows,type) {
  if(rows.length<2 || rows.length>201 || rows[0].length!==2)throw Error('Selecione duas colunas, com cabeçalho e de 1 a 200 linhas de dados.');
  const points=rows.slice(1).filter(r=>r.some(v=>v!==''&&v!=null)).map(r=>{
    if(r[1]===''||r[1]==null||!Number.isFinite(Number(r[1])))throw Error('A segunda coluna deve conter números ou resultados numéricos.');
    return {label:String(r[0]??''),value:Number(r[1])};
  });
  if(!points.length)throw Error('Preencha o intervalo antes de criar um gráfico.');
  if(['pie','doughnut'].includes(type)&&(points.some(p=>p.value<0)||!points.some(p=>p.value>0)))throw Error('Pizza exige valores não negativos e total maior que zero.');
  if(type==='scatter'&&points.some(point=>!point.label.trim()||!Number.isFinite(Number(point.label))))throw Error('Dispersão exige números nas duas colunas.');
  if(type==='radar'&&(points.length<3||points.some(point=>point.value<0)))throw Error('Radar exige pelo menos três valores não negativos.');
  return points;
}
export function chartSvg(rows,{title,type}) {
  const p=chartData(rows,type),W=720,H=360;let body='';
  if(type==='pie'||type==='doughnut'){
    const sum=p.reduce((s,v)=>s+v.value,0);let angle=-Math.PI/2;
    p.forEach((v,i)=>{if(!v.value)return;const a=angle,b=a+v.value/sum*Math.PI*2;angle=b;
      const fill=palette[i%palette.length];const tip=escape(v.label+': '+v.value+' ('+(v.value/sum*100).toFixed(1)+'%)');
      body+=v.value===sum?`<circle cx="240" cy="190" r="125" fill="${fill}"><title>${tip}</title></circle>`:`<path d="M240 190 L${240+125*Math.cos(a)} ${190+125*Math.sin(a)} A125 125 0 ${b-a>Math.PI?1:0} 1 ${240+125*Math.cos(b)} ${190+125*Math.sin(b)} Z" fill="${fill}" stroke="white"><title>${tip}</title></path>`;
    });
    if(type==='doughnut')body+='<circle cx="240" cy="190" r="65" fill="white"/>';
    p.slice(0,12).forEach((v,i)=>body+=`<rect x="415" y="${58+i*23}" width="12" height="12" fill="${palette[i%palette.length]}"/><text x="435" y="${69+i*23}" font-size="12">${escape(v.label.slice(0,28))}: ${v.value}</text>`);
  } else if(type==='radar'){
    const max=Math.max(1,...p.map(v=>v.value)),point=(i,value)=>[360+120*value/max*Math.sin(i/p.length*Math.PI*2),190-120*value/max*Math.cos(i/p.length*Math.PI*2)];
    for(let level=1;level<=4;level++)body+=`<polygon points="${p.map((_,i)=>point(i,max*level/4).join(',')).join(' ')}" fill="none" stroke="#dce4da"/>`;
    body+=`<polygon points="${p.map((v,i)=>point(i,v.value).join(',')).join(' ')}" fill="#4b532044" stroke="#4b5320"/>`;
    p.forEach((v,i)=>{const [x,y]=point(i,max*1.15);body+=`<text x="${x}" y="${y}" text-anchor="middle" font-size="11">${escape(v.label.slice(0,18))}</text>`;});
  } else if(type==='horizontal'){
    const min=Math.min(0,...p.map(v=>v.value)),max=Math.max(0,...p.map(v=>v.value)),span=max-min||1,x=value=>160+(value-min)/span*520,step=260/p.length;
    p.forEach((v,i)=>{body+=`<text x="150" y="${61+i*step}" text-anchor="end" font-size="11">${escape(v.label.slice(0,20))}</text><rect x="${Math.min(x(0),x(v.value))}" y="${48+i*step}" width="${Math.max(1,Math.abs(x(v.value)-x(0)))}" height="${step*.7}" fill="${palette[i%palette.length]}"><title>${v.value}</title></rect>`;});
  } else {
    const min=Math.min(0,...p.map(v=>v.value)),max=Math.max(0,...p.map(v=>v.value)),span=max-min||1;
    const xmin=Math.min(...p.map(v=>Number(v.label))),xmax=Math.max(...p.map(v=>Number(v.label)));
    const y=v=>295-(v-min)/span*240,step=610/p.length,x=i=>type==='scatter'?80+(Number(p[i].label)-xmin)/(xmax-xmin||1)*600:80+step*(i+.5),zero=y(0);
    for(let i=0;i<=4;i++){const v=min+span*i/4,yy=y(v);body+=`<path d="M70 ${yy} H700" stroke="#dce4da"/><text x="62" y="${yy+4}" text-anchor="end" font-size="11">${escape(Number(v.toPrecision(5)))}</text>`;}
    if(type==='area')body+=`<polygon points="${x(0)},${zero} ${p.map((v,i)=>x(i)+','+y(v.value)).join(' ')} ${x(p.length-1)},${zero}" fill="#78904855"/>`;
    if(['line','area'].includes(type))body+=`<polyline points="${p.map((v,i)=>x(i)+','+y(v.value)).join(' ')}" fill="none" stroke="#4b5320" stroke-width="3"/>`;
    p.forEach((v,i)=>{
      const tip=`<title>${escape(v.label)}: ${v.value}</title>`;
      body+=['line','area','scatter'].includes(type)?`<circle cx="${x(i)}" cy="${y(v.value)}" r="4" fill="#4b5320">${tip}</circle>`:`<rect x="${x(i)-step*.35}" y="${Math.min(zero,y(v.value))}" width="${step*.7}" height="${Math.max(1,Math.abs(zero-y(v.value)))}" fill="${palette[i%palette.length]}">${tip}</rect>`;
      if(i%Math.max(1,Math.ceil(p.length/10))===0)body+=`<text x="${x(i)}" y="320" text-anchor="middle" font-size="11">${escape(v.label.slice(0,12))}</text>`;
    });
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${escape(title)}"><rect width="720" height="360" fill="white"/><g fill="#23332e" font-family="Arial,sans-serif"><text x="360" y="25" text-anchor="middle" font-size="18" font-weight="bold">${escape(title)}</text>${body}</g></svg>`;
}
