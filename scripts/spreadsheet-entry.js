import {createUniver} from '@univerjs/presets';
import {LocaleType,mergeLocales} from '@univerjs/core';
import {UniverSheetsCorePreset} from '@univerjs/preset-sheets-core';
import {UniverSheetsFilterPreset} from '@univerjs/preset-sheets-filter';
import {UniverSheetsSortPreset} from '@univerjs/preset-sheets-sort';
import {UniverSheetsDataValidationPreset} from '@univerjs/preset-sheets-data-validation';
import {UniverSheetsConditionalFormattingPreset} from '@univerjs/preset-sheets-conditional-formatting';
import coreLocale from '@univerjs/preset-sheets-core/locales/pt-BR';
import filterLocale from '@univerjs/preset-sheets-filter/locales/pt-BR';
import sortLocale from '@univerjs/preset-sheets-sort/locales/pt-BR';
import validationLocale from '@univerjs/preset-sheets-data-validation/locales/pt-BR';
import conditionalLocale from '@univerjs/preset-sheets-conditional-formatting/locales/pt-BR';
import '@univerjs/preset-sheets-core/lib/index.css';
import '@univerjs/preset-sheets-filter/lib/index.css';
import '@univerjs/preset-sheets-sort/lib/index.css';
import '@univerjs/preset-sheets-data-validation/lib/index.css';
import '@univerjs/preset-sheets-conditional-formatting/lib/index.css';
import {toWorkbook,workbookRows} from '../web/spreadsheet-model.js';
import {normalizeFormula,parseCSV,toCSV} from '../web/formula.js';
export {toWorkbook,workbookRows};
export async function mountSpreadsheet(container,content,{id,name,readOnly,onChange,onError,onRender=()=>{}}) {
  const snapshot=toWorkbook(content,id,name);
  // Keep existing localized formulas executable, without touching quoted text.
  for(const sheet of Object.values(snapshot.sheets)) for(const row of Object.values(sheet.cellData||{})) for(const cell of Object.values(row||{})) if(cell?.f) cell.f=normalizeFormula(cell.f);
  const {univer,univerAPI}=createUniver({locale:LocaleType.PT_BR,locales:{[LocaleType.PT_BR]:mergeLocales(coreLocale,filterLocale,sortLocale,validationLocale,conditionalLocale)},presets:[
    UniverSheetsCorePreset({menu:Object.fromEntries(['sheet.contextMenu.permission','sheet.command.add-range-protection-from-toolbar','sheet.command.add-range-protection-from-sheet-bar','sheet.command.view-sheet-permission-from-sheet-bar','sheet.command.delete-worksheet-protection-from-sheet-bar','sheet.command.change-sheet-protection-from-sheet-bar'].map(id=>[id,{hidden:true}])),container,header:true,toolbar:true,formulaBar:true,footer:true,ribbonType:'classic'}),
    UniverSheetsFilterPreset(),UniverSheetsSortPreset(),UniverSheetsDataValidationPreset(),UniverSheetsConditionalFormattingPreset(),
  ]});
  const book=univerAPI.createWorkbook(snapshot);
  if(readOnly) {
    container.inert=true;
    // Snapshot permission initialization is asynchronous. Apply the app's read
    // role after initialization so it cannot be replaced by the SDK defaults.
    if(univerAPI.getCurrentLifecycleStage()<3) await new Promise(resolve=>{
      const listener=univerAPI.addEvent(univerAPI.Event.LifeCycleChanged,({stage})=>{if(stage>=3){listener.dispose();resolve();}});
    });
    await book.getWorkbookPermission().setReadOnly();book.setEditable(false);
    container.inert=false;
  }
  let disposed=false,timer;
  const sync=()=>{
    if(disposed) return;
    content.workbook=book.save();
    // Remove the redundant legacy matrices after migrating; old server versions
    // remain in history and are still understood by toWorkbook.
    delete content.cells;delete content.sheets;delete content.activeSheet;
  };
  const subscription=book.onCommandExecuted(command=>{
    if(disposed||command.type!==2)return;
    if(!readOnly&&!command.id.startsWith('formula.'))onChange();clearTimeout(timer);timer=setTimeout(()=>{try{sync();onRender();}catch(e){onError(e.message);}},50);
  });
  return {
    async flush(){await book.endEditingAsync(true);clearTimeout(timer);sync();},
    snapshot(){sync();return content.workbook;},
    dispose(){disposed=true;clearTimeout(timer);subscription.dispose();univer.dispose();},
    select(address){const range=book.getActiveSheet().getRange(address);range.activate();return range;},
    set(address,value){if(readOnly)return;const range=book.getActiveSheet().getRange(address);range.setValue(typeof value==='string'&&value.startsWith('=')?normalizeFormula(value):value);range.activate();sync();onChange();},
    read(address){const range=book.getActiveSheet().getRange(address);return {values:range.getValues(),formulas:range.getFormulas()};},
    async paste(text,address){if(readOnly)return;const rows=text.includes('\t')?text.replace(/\r/g,'').replace(/\n$/,'').split('\n').map(r=>r.split('\t')):parseCSV(text,{maxRows:10000,maxCols:256,minCols:1});const anchor=book.getActiveSheet().getRange(address);const pos=anchor.getRange();const width=Math.max(...rows.map(r=>r.length));if(rows.length>10000||width>256||rows.length*width>50000)throw Error('Limite de colagem: 50 mil células, 10 mil linhas e 256 colunas.');const sheet=book.getActiveSheet();if(pos.startRow+rows.length>sheet.getMaxRows())sheet.insertRowsAfter(sheet.getMaxRows()-1,pos.startRow+rows.length-sheet.getMaxRows());if(pos.startColumn+width>sheet.getMaxColumns())sheet.insertColumnsAfter(sheet.getMaxColumns()-1,pos.startColumn+width-sheet.getMaxColumns());const values=rows.map(r=>Array.from({length:width},(_,i)=>r[i]??''));book.getActiveSheet().getRange(pos.startRow,pos.startColumn,rows.length,width).setValues(values);sync();onChange();},
    csv(){sync();return toCSV(workbookRows(content.workbook,book.getActiveSheet().getSheetId()));},
    rows(){sync();return workbookRows(content.workbook,book.getActiveSheet().getSheetId());},
    activeSheetId(){return book.getActiveSheet().getSheetId();},
    chartRows(address,sheetId){const sheet=book.getSheetBySheetId(sheetId);if(!sheet)throw Error('A aba de origem foi removida.');const range=sheet.getRange(address);const r=range.getRange();if(r.endRow-r.startRow>200||r.endColumn-r.startColumn!==1)throw Error('Selecione duas colunas, cabeçalho e até 200 linhas de dados.');return range.getValues();},
    api:univerAPI,
  };
}
