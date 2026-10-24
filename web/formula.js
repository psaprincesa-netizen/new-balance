import FormulaParser, { aliases } from './formula-engine.js';
// Parse expressions with the MIT-licensed Excel grammar; never evaluate JavaScript.

export function normalizeFormula(raw) {
  return raw.replace(/"(?:[^" ]| |"")*"|'(?:[^']|'')*'|[^"']+/g, part => {
    if (part.startsWith('"') || part.startsWith("'")) return part;
    return part.replace(/[\p{L}_.]+(?=\s*\()/gu, name => aliases[name.toUpperCase()] || name).replaceAll(';', ',');
  });
}
const flat = args => args.flatMap(arg => [arg?.value ?? arg].flat(Infinity));
const numbers = args => flat(args).filter(v => typeof v === 'number' && Number.isFinite(v));
const value = (arg, fallback=0) => Number(arg?.value ?? fallback);
const variance = args => {const a=numbers(args); if(a.length<2) throw FormulaParser.FormulaError.DIV0; const avg=a.reduce((s,v)=>s+v,0)/a.length; return a.reduce((s,v)=>s+(v-avg)**2,0)/(a.length-1);};
const extraFunctions = {
  MIN:(...a)=>Math.min(...numbers(a)), MAX:(...a)=>Math.max(...numbers(a)),
  MEDIAN:(...a)=>{const n=numbers(a).sort((x,y)=>x-y); if(!n.length) throw FormulaParser.FormulaError.NUM; return (n[Math.floor((n.length-1)/2)]+n[Math.floor(n.length/2)])/2;},
  COUNTA:(...a)=>flat(a).filter(v=>v!==null && v!==undefined && v!=='').length,
  LEN:a=>String(a?.value ?? '').length, UPPER:a=>String(a?.value ?? '').toUpperCase(),
  'VAR.S':(...a)=>variance(a), 'STDEV.S':(...a)=>Math.sqrt(variance(a)),
  PMT:(r,n,pv,fv,t)=>{r=value(r);n=value(n);pv=value(pv);fv=value(fv);t=value(t);if(n<=0 || r<=-1 || ![0,1].includes(t))throw FormulaParser.FormulaError.NUM;return r===0?-(pv+fv)/n:-(r*(pv*(1+r)**n+fv))/((1+r*t)*((1+r)**n-1));},
  FV:(r,n,pmt,pv,t)=>{r=value(r);n=value(n);pmt=value(pmt);pv=value(pv);t=value(t);return r===0?-(pv+pmt*n):-(pv*(1+r)**n+pmt*(1+r*t)*((1+r)**n-1)/r);},
  PV:(r,n,pmt,fv,t)=>{r=value(r);n=value(n);pmt=value(pmt);fv=value(fv);t=value(t);return r===0?-(fv+pmt*n):-(fv+pmt*(1+r*t)*((1+r)**n-1)/r)/(1+r)**n;},
};
export function cellValue(grid, row, col, seen=new Set(), sheets=null, sheetName=null) {
  const raw=String(grid[row]?.[col] ?? '');
  if(!raw.startsWith('=')) return raw;
  const name=sheetName || sheets?.find(s=>s.cells===grid)?.name || 'Planilha 1';
  const key=name.toLowerCase()+':'+row+':'+col;
  if(seen.has(key)||seen.size>80) return '#CICLO!';
  if(raw.length>2000) return '#LIMITE!';
  const chain=new Set(seen).add(key);
  const E=FormulaParser.FormulaError;
  const resolveSheet=label=> {
    if(!label || label.toLowerCase()===name.toLowerCase()) return grid;
    const sheet=sheets?.find(s=>s.name.toLowerCase()===label.toLowerCase());
    if(!sheet) throw E.REF;
    return sheet.cells;
  };
  const get=({sheet,row:r,col:c})=> {
    const cells=resolveSheet(sheet);
    if(r<1||c<1||r>cells.length||c>cells[0].length) throw E.ERROR('Cell outside workspace');
    const result=cellValue(cells,r-1,c-1,chain,sheets,sheet || name);
    if(String(result).startsWith('#')) throw new E(String(result));
    if(result==='') return null;
    if(/^(TRUE|FALSE)$/i.test(String(result))) return String(result).toUpperCase()==='TRUE';
    return typeof result==='number' || /^[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?$/i.test(result) ? Number(result) : result;
  };
  try {
    const expression=normalizeFormula(raw.slice(1));
    if(/\b(?:WEBSERVICE|HYPERLINK|IMPORTXML|IMPORTDATA)\s*\(/i.test(expression) || /^SUM\(\s*\)$/i.test(expression)) return '#ERRO!';
    const parser=new FormulaParser({functions:extraFunctions,functionsNeedContext:{WEBSERVICE:()=>{throw E.NAME;}},onCell:get,onRange:ref=>{
      const cells=resolveSheet(ref.sheet);
      // Whole-column/row references are bounded by the editor's actual grid.
      const lastRow=ref.to.row===FormulaParser.MAX_ROW?cells.length:ref.to.row;
      const lastCol=ref.to.col===FormulaParser.MAX_COLUMN?cells[0].length:ref.to.col;
      if(lastRow>cells.length||lastCol>cells[0].length||ref.from.row<1||ref.from.col<1)throw E.REF;
      return Array.from({length:lastRow-ref.from.row+1},(_,r)=>Array.from({length:lastCol-ref.from.col+1},(_,c)=>get({sheet:ref.sheet,row:r+ref.from.row,col:c+ref.from.col})));
    }});
    const result=parser.parse(expression,{row:row+1,col:col+1,sheet:name});
    if(result instanceof E) throw result;
    if(typeof result==='number') return Number.isFinite(result)?Number(result.toFixed(10)):'#NUM!';
    if(typeof result==='boolean')return result?'TRUE':'FALSE';
    return result ?? '';
  } catch(e) {
    for (let depth=0; depth<8 && e.name==='#ERROR!' && e.details instanceof Error; depth++) e=e.details;
    return ['#CICLO!','#DIV/0!','#N/A','#VALUE!','#NUM!'].includes(e.name)?e.name:'#ERRO!';
  }
}

export function parseCSV(text, {maxRows=200,maxCols=26,minCols=6}={}) {
  const rows = [[]];
  let value = "",
    quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      if (quoted && text[i + 1] === '"') {
        value += '"';
        i++;
      } else if (quoted || !value) quoted = !quoted;
      else value += ch;
    } else if (!quoted && (ch === "," || ch === ";")) {
      rows.at(-1).push(value);
      value = "";
    } else if (!quoted && (ch === "\n" || ch === "\r")) {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      rows.at(-1).push(value);
      rows.push([]);
      value = "";
    } else value += ch;
  }
  if (quoted) throw Error("CSV com aspas não fechadas.");
  rows.at(-1).push(value);
  if (rows.length > 1 && rows.at(-1).length === 1 && rows.at(-1)[0] === "")
    rows.pop();
  if (rows.length > maxRows || Math.max(...rows.map((r) => r.length)) > maxCols)
    throw Error(`Limite: ${maxRows} linhas e ${maxCols} colunas.`);
  const width = Math.max(minCols, ...rows.map((r) => r.length));
  return rows.map((r) => Array.from({ length: width }, (_, i) => r[i] || ""));
}
export function toCSV(rows) {
  return rows
    .map((r) =>
      r.map((v) => '"' + String(v ?? "").replaceAll('"', '""') + '"').join(","),
    )
    .join("\r\n");
}
