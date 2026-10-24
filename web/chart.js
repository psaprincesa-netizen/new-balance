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
  if(type==='pie'&&(points.some(p=>p.value<0)||!points.some(p=>p.value>0)))throw Error('Pizza exige valores não negativos e total maior que zero.');
  return points;
}
export function chartSvg(rows,{title,type}) {
  const p=chartData(rows,type),W=720,H=360;let body='';
  if(type==='pie'){
    const sum=p.reduce((s,v)=>s+v.value,0);let angle=-Math.PI/2;
    p.forEach((v,i)=>{if(!v.value)return;const a=angle,b=a+v.value/sum*Math.PI*2;angle=b;
      const fill=palette[i%palette.length];const tip=escape(v.label+': '+v.value+' ('+(v.value/sum*100).toFixed(1)+'%)');
      body+=v.value===sum?`<circle cx="240" cy="190" r="125" fill="${fill}"><title>${tip}</title></circle>`:`<path d="M240 190 L${240+125*Math.cos(a)} ${190+125*Math.sin(a)} A125 125 0 ${b-a>Math.PI?1:0} 1 ${240+125*Math.cos(b)} ${190+125*Math.sin(b)} Z" fill="${fill}" stroke="white"><title>${tip}</title></path>`;
    });
    p.slice(0,12).forEach((v,i)=>body+=`<rect x="415" y="${58+i*23}" width="12" height="12" fill="${palette[i%palette.length]}"/><text x="435" y="${69+i*23}" font-size="12">${escape(v.label.slice(0,28))}: ${v.value}</text>`);
  } else {
    const min=Math.min(0,...p.map(v=>v.value)),max=Math.max(0,...p.map(v=>v.value)),span=max-min||1;
    const y=v=>295-(v-min)/span*240,step=610/p.length,x=i=>80+step*(i+.5),zero=y(0);
    for(let i=0;i<=4;i++){const v=min+span*i/4,yy=y(v);body+=`<path d="M70 ${yy} H700" stroke="#dce4da"/><text x="62" y="${yy+4}" text-anchor="end" font-size="11">${escape(Number(v.toPrecision(5)))}</text>`;}
    if(type==='line')body+=`<polyline points="${p.map((v,i)=>x(i)+','+y(v.value)).join(' ')}" fill="none" stroke="#4b5320" stroke-width="3"/>`;
    p.forEach((v,i)=>{
      const tip=`<title>${escape(v.label)}: ${v.value}</title>`;
      body+=type==='line'?`<circle cx="${x(i)}" cy="${y(v.value)}" r="4" fill="#4b5320">${tip}</circle>`:`<rect x="${x(i)-step*.35}" y="${Math.min(zero,y(v.value))}" width="${step*.7}" height="${Math.max(1,Math.abs(zero-y(v.value)))}" fill="${palette[i%palette.length]}">${tip}</rect>`;
      if(i%Math.max(1,Math.ceil(p.length/10))===0)body+=`<text x="${x(i)}" y="320" text-anchor="middle" font-size="11">${escape(v.label.slice(0,12))}</text>`;
    });
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${escape(title)}"><rect width="720" height="360" fill="white"/><g fill="#23332e" font-family="Arial,sans-serif"><text x="360" y="25" text-anchor="middle" font-size="18" font-weight="bold">${escape(title)}</text>${body}</g></svg>`;
}
