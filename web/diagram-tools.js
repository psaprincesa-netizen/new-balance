export const DIAGRAM_SHAPES = {process:'Processo', decision:'Decisão', terminator:'Início/fim', database:'Banco de dados', document:'Documento'};
const templates = {
  flow: {title:'Fluxograma de aprovação',nodes:['Início','Preparar solicitação','Aprovado?','Executar','Revisar'],positions:[{x:30,y:30},{x:260,y:30},{x:490,y:30},{x:720,y:30},{x:490,y:200}],shapes:['terminator','document','decision','process','process'],edges:[{from:0,to:1},{from:1,to:2},{from:2,to:3,label:'Sim'},{from:2,to:4,label:'Não'},{from:4,to:1}]},
  organization: {title:'Organograma',nodes:['Direção','Operações','Produto','Atendimento','Engenharia'],positions:[{x:380,y:30},{x:160,y:180},{x:600,y:180},{x:160,y:330},{x:600,y:330}],shapes:['process','process','process','process','process'],edges:[{from:0,to:1},{from:0,to:2},{from:1,to:3},{from:2,to:4}]},
  network: {title:'Arquitetura de aplicação',nodes:['Usuário','Aplicação web','API','Banco de dados','Armazenamento'],positions:[{x:30,y:40},{x:260,y:40},{x:490,y:40},{x:720,y:40},{x:490,y:230}],shapes:['terminator','process','process','database','database'],edges:[{from:0,to:1,label:'HTTPS'},{from:1,to:2,label:'JSON'},{from:2,to:3,label:'Dados'},{from:2,to:4,label:'Arquivos'}]},
};
export const DIAGRAM_TEMPLATES = Object.fromEntries(Object.entries(templates).map(([key,value])=>[key,value.title]));
export function diagramTemplate(key) {
  if(!Object.hasOwn(templates,key))throw Error('Modelo de diagrama inválido.');
  const {title,...content}=structuredClone(templates[key]);return {kind:'diagram',title,content};
}
export function nodeShape(shape) {
  const style='fill="#f2f4e9" stroke="#4b5320" stroke-width="2"';
  if(shape==='decision')return `<polygon points="80,0 160,30 80,60 0,30" ${style}/>`;
  if(shape==='terminator')return `<ellipse cx="80" cy="30" rx="80" ry="30" ${style}/>`;
  if(shape==='database')return `<path d="M0 10 C0 -3 160 -3 160 10 L160 50 C160 63 0 63 0 50 Z M0 10 C0 23 160 23 160 10" ${style}/>`;
  if(shape==='document')return `<path d="M0 0 H160 V50 Q120 35 80 50 T0 50 Z" ${style}/>`;
  return `<rect width="160" height="60" rx="6" ${style}/>`;
}
function boundary(p,dx,dy,shape) {
  if(!dx&&!dy)return {x:p.x+80,y:p.y+30};
  const ratio=shape==='decision'?1/(Math.abs(dx)/80+Math.abs(dy)/30):shape==='terminator'?1/Math.sqrt((dx/80)**2+(dy/30)**2):Math.min(80/Math.abs(dx||1e-20),30/Math.abs(dy||1e-20));
  return {x:p.x+80+dx*ratio,y:p.y+30+dy*ratio};
}
export function edgeGeometry(a,b,fromShape='process',toShape='process') {
  const dx=b.x-a.x,dy=b.y-a.y,from=boundary(a,dx,dy,fromShape),to=boundary(b,-dx,-dy,toShape);
  return {x1:from.x,y1:from.y,x2:to.x,y2:to.y,labelX:(from.x+to.x)/2,labelY:(from.y+to.y)/2-8};
}
