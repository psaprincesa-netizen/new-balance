// Lossless migration of the original DRAP cell arrays to a sparse workbook.
export function toWorkbook(content, id='workbook', name='Planilha') {
  if (content.workbook) return structuredClone(content.workbook);
  const source=content.sheets || [{name:'Planilha 1',cells:content.cells || [['']]}];
  const sheets={}; const sheetOrder=[];
  source.forEach((entry,i)=>{
    const key='sheet-'+i;sheetOrder.push(key);const cellData={};
    entry.cells.forEach((row,r)=>row.forEach((value,c)=>{
      if(value==='') return;
      cellData[r] ??={};
      if(String(value).startsWith('=')) cellData[r][c]={f:String(value)};
      else if(/^[-+]?(?:0|[1-9]\d*)(?:\.\d+)?(?:e[-+]?\d+)?$/i.test(String(value))) cellData[r][c]={v:Number(value),t:2};
      else cellData[r][c]={v:String(value),t:1};
    }));
    sheets[key]={id:key,name:entry.name,rowCount:Math.max(1000,entry.cells.length),columnCount:Math.max(26,entry.cells[0]?.length||1),cellData,defaultColumnWidth:105,defaultRowHeight:25,mergeData:[]};
  });
  return {id,name,appVersion:'1.2.0',locale:'ptBR',styles:{},sheetOrder,sheets};
}
export function workbookRows(workbook, sheetId=workbook.sheetOrder[0], formulas=false) {
  const data=workbook.sheets[sheetId]?.cellData || {};
  let height=1,width=1;
  for (const [r,cols] of Object.entries(data)) for(const [c,cell] of Object.entries(cols||{})) {
    if (cell && (cell.v!=null || cell.f || cell.p)) {height=Math.max(height,+r+1);width=Math.max(width,+c+1);}
  }
  if(height*width>100000) throw Error('A área de exportação excede 100 mil células. Selecione uma área menor.');
  return Array.from({length:height},(_,r)=>Array.from({length:width},(_,c)=>{
    const cell=data[r]?.[c];return formulas&&cell?.f?cell.f:cell?.v ?? cell?.p?.body?.dataStream?.trimEnd() ?? '';
  }));
}
