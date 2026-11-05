// Small SVG charts of live worksheet ranges. No remote renderer or scripts.
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const palette=['#4b5320','#789048','#a7b77e','#314d44','#6c8f85','#b29c68','#535d77','#ad795c'];
export const CHART_TYPES={bar:'Colunas',stacked:'Colunas empilhadas',hbar:'Barras horizontais',line:'Linhas',area:'Área',pie:'Pizza',doughnut:'Rosca',scatter:'Dispersão (X e Y numéricos)'};
const SINGLE_SERIES=new Set(['pie','doughnut']);
const number=v=>v!==''&&v!=null&&Number.isFinite(Number(v));
const fmt=v=>escape(Number(Number(v).toPrecision(5)));
// Tooltip label: the category alone for one series, category · series for several.
const tip=(d,i,s)=>d.series.length>1?d.labels[i]+' · '+s.name:d.labels[i];

// rows: header + data rows; first column = labels (or X for scatter), next 1..6 columns = numeric series.
export function chartData(rows,type='bar') {
  const width=rows[0]?.length||0;
  if(rows.length<2||rows.length>201||width<2||width>7)throw Error('Selecione de 2 a 7 colunas (rótulos e até 6 séries), com cabeçalho e de 1 a 200 linhas de dados.');
  if(SINGLE_SERIES.has(type)&&width!==2)throw Error('Pizza e rosca usam duas colunas: rótulos e valores.');
  const data=rows.slice(1).filter(r=>r.some(v=>v!==''&&v!=null));
  if(!data.length)throw Error('Preencha o intervalo antes de criar um gráfico.');
  for(const r of data)for(let c=1;c<width;c++)if(!number(r[c]))throw Error('As colunas de valores devem conter números ou resultados numéricos.');
  if(type==='scatter'&&data.some(r=>!number(r[0])))throw Error('Na dispersão, a primeira coluna (X) também deve ser numérica.');
  const series=rows[0].slice(1).map((name,i)=>({name:String(name??'')||'Série '+(i+1),values:data.map(r=>Number(r[i+1]))}));
  if(SINGLE_SERIES.has(type)){const v=series[0].values;if(v.some(x=>x<0)||!v.some(x=>x>0))throw Error('Pizza e rosca exigem valores não negativos e total maior que zero.');}
  return {labels:data.map(r=>String(r[0]??'')),x:type==='scatter'?data.map(r=>Number(r[0])):null,series};
}

function legend(series,x0=90,y0=338){
  if(series.length<2)return '';
  return series.map((s,i)=>`<rect x="${x0+i*105}" y="${y0}" width="10" height="10" fill="${palette[i%palette.length]}"/><text x="${x0+14+i*105}" y="${y0+9}" font-size="11">${escape(s.name.slice(0,14))}</text>`).join('');
}

function radial(d,donut){
  const values=d.series[0].values,sum=values.reduce((s,v)=>s+v,0);let angle=-Math.PI/2,body='';
  const R=125,r=donut?70:0,cx=240,cy=190,pt=(rad,a)=>`${cx+rad*Math.cos(a)} ${cy+rad*Math.sin(a)}`;
  values.forEach((v,i)=>{if(!v)return;const a=angle,b=a+v/sum*Math.PI*2;angle=b;
    const fill=palette[i%palette.length],tip=escape(d.labels[i]+': '+v+' ('+(v/sum*100).toFixed(1)+'%)'),large=b-a>Math.PI?1:0;
    if(v===sum)body+=donut?`<circle cx="${cx}" cy="${cy}" r="${(R+r)/2}" fill="none" stroke="${fill}" stroke-width="${R-r}"><title>${tip}</title></circle>`:`<circle cx="${cx}" cy="${cy}" r="${R}" fill="${fill}"><title>${tip}</title></circle>`;
    else body+=`<path d="M${pt(R,a)} A${R} ${R} 0 ${large} 1 ${pt(R,b)} ${donut?`L${pt(r,b)} A${r} ${r} 0 ${large} 0 ${pt(r,a)}`:`L${cx} ${cy}`} Z" fill="${fill}" stroke="white"><title>${tip}</title></path>`;
  });
  if(donut)body+=`<text x="${cx}" y="${cy+6}" text-anchor="middle" font-size="16" font-weight="bold">${fmt(sum)}</text>`;
  d.labels.slice(0,12).forEach((l,i)=>body+=`<rect x="415" y="${58+i*23}" width="12" height="12" fill="${palette[i%palette.length]}"/><text x="435" y="${69+i*23}" font-size="12">${escape(l.slice(0,28))}: ${values[i]}</text>`);
  return body;
}

function axes(min,max,y){
  let body='';const span=max-min||1;
  for(let i=0;i<=4;i++){const v=min+span*i/4,yy=y(v);body+=`<path d="M70 ${yy} H700" stroke="#dce4da"/><text x="62" y="${yy+4}" text-anchor="end" font-size="11">${fmt(v)}</text>`;}
  return body;
}

function cartesian(d,type){
  const n=d.labels.length,stacked=type==='stacked';
  let min=0,max=0;
  if(stacked){for(let i=0;i<n;i++){let pos=0,neg=0;for(const s of d.series){const v=s.values[i];if(v>=0)pos+=v;else neg+=v;}max=Math.max(max,pos);min=Math.min(min,neg);}}
  else for(const s of d.series)for(const v of s.values){min=Math.min(min,v);max=Math.max(max,v);}
  const span=max-min||1,y=v=>295-(v-min)/span*240,step=610/n,x=i=>80+step*(i+.5),zero=y(0);
  let body=axes(min,max,y);
  if(type==='bar'){
    const w=step*.7/d.series.length;
    d.series.forEach((s,k)=>s.values.forEach((v,i)=>{body+=`<rect x="${x(i)-step*.35+k*w}" y="${Math.min(zero,y(v))}" width="${Math.max(1,w-1)}" height="${Math.max(1,Math.abs(zero-y(v)))}" fill="${palette[(d.series.length>1?k:i)%palette.length]}"><title>${escape(tip(d,i,s))}: ${v}</title></rect>`;}));
  } else if(stacked){
    for(let i=0;i<n;i++){let pos=0,neg=0;d.series.forEach((s,k)=>{const v=s.values[i],base=v>=0?pos:neg,top=base+v;if(v>=0)pos=top;else neg=top;
      body+=`<rect x="${x(i)-step*.35}" y="${Math.min(y(base),y(top))}" width="${step*.7}" height="${Math.max(1,Math.abs(y(base)-y(top)))}" fill="${palette[k%palette.length]}"><title>${escape(tip(d,i,s))}: ${v}</title></rect>`;});}
  } else {
    d.series.forEach((s,k)=>{const color=palette[k%palette.length],pts=s.values.map((v,i)=>x(i)+','+y(v)).join(' ');
      if(type==='area')body+=`<polygon points="${x(0)},${zero} ${pts} ${x(n-1)},${zero}" fill="${color}" fill-opacity="${d.series.length>1?0.35:0.55}" stroke="${color}" stroke-width="2"/>`;
      else body+=`<polyline points="${pts}" fill="none" stroke="${color}" stroke-width="3"/>`;
      s.values.forEach((v,i)=>body+=`<circle cx="${x(i)}" cy="${y(v)}" r="${type==='area'?3:4}" fill="${color}"><title>${escape(tip(d,i,s))}: ${v}</title></circle>`);});
  }
  d.labels.forEach((l,i)=>{if(i%Math.max(1,Math.ceil(n/10))===0)body+=`<text x="${x(i)}" y="320" text-anchor="middle" font-size="11">${escape(l.slice(0,12))}</text>`;});
  return body+legend(d.series);
}

function horizontal(d){
  const n=d.labels.length;let min=0,max=0;for(const s of d.series)for(const v of s.values){min=Math.min(min,v);max=Math.max(max,v);}
  const span=max-min||1,X=v=>170+(v-min)/span*510,step=270/n,Y=i=>45+step*i,zero=X(0),h=step*.75/d.series.length;let body='';
  for(let i=0;i<=4;i++){const v=min+span*i/4,xx=X(v);body+=`<path d="M${xx} 40 V318" stroke="#dce4da"/><text x="${xx}" y="332" text-anchor="middle" font-size="11">${fmt(v)}</text>`;}
  d.series.forEach((s,k)=>s.values.forEach((v,i)=>{body+=`<rect x="${Math.min(zero,X(v))}" y="${Y(i)+step*.125+k*h}" width="${Math.max(1,Math.abs(X(v)-zero))}" height="${Math.max(1,h-1)}" fill="${palette[(d.series.length>1?k:i)%palette.length]}"><title>${escape(tip(d,i,s))}: ${v}</title></rect>`;}));
  d.labels.forEach((l,i)=>{if(n<=25||i%Math.ceil(n/25)===0)body+=`<text x="162" y="${Y(i)+step/2+4}" text-anchor="end" font-size="11">${escape(l.slice(0,22))}</text>`;});
  return body+legend(d.series,90,342);
}

function scatter(d){
  const xs=d.x;let ymin=Infinity,ymax=-Infinity;for(const s of d.series)for(const v of s.values){ymin=Math.min(ymin,v);ymax=Math.max(ymax,v);}
  const xmin=Math.min(...xs),xmax=Math.max(...xs),xs_=xmax-xmin||1,ys=ymax-ymin||1;
  const X=v=>80+(v-xmin)/xs_*610,Y=v=>295-(v-ymin)/ys*240;let body=axes(ymin,ymax,Y);
  for(let i=0;i<=4;i++){const v=xmin+xs_*i/4;body+=`<text x="${X(v)}" y="320" text-anchor="middle" font-size="11">${fmt(v)}</text>`;}
  d.series.forEach((s,k)=>s.values.forEach((v,i)=>body+=`<circle cx="${X(xs[i])}" cy="${Y(v)}" r="5" fill="${palette[k%palette.length]}" fill-opacity="0.85"><title>${escape(s.name)}: (${xs[i]}, ${v})</title></circle>`));
  return body+legend(d.series);
}

export function chartSvg(rows,{title,type}) {
  const d=chartData(rows,type),W=720,H=360;
  const body=type==='pie'||type==='doughnut'?radial(d,type==='doughnut'):type==='hbar'?horizontal(d):type==='scatter'?scatter(d):cartesian(d,type);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${escape(title)}"><rect width="720" height="360" fill="white"/><g fill="#23332e" font-family="Arial,sans-serif"><text x="360" y="25" text-anchor="middle" font-size="18" font-weight="bold">${escape(title)}</text>${body}</g></svg>`;
}
