import {createUniver} from '@univerjs/presets';
import {CommandType,ICommandService,LocaleType,mergeLocales} from '@univerjs/core';
import {SelectionMoveType} from '@univerjs/sheets';
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
import {parsePivotRange} from '../web/pivot.js';
import {toWorkbook,workbookRows} from '../web/spreadsheet-model.js';
import {normalizeFormula,parseCSV,toCSV} from '../web/formula.js';
export {toWorkbook,workbookRows};
export async function mountSpreadsheet(container,content,{id,name,readOnly,onChange,onError,onRender=()=>{},onSelection=()=>{}}) {
  const snapshot=toWorkbook(content,id,name);
  // Keep existing localized formulas executable, without touching quoted text.
  for(const sheet of Object.values(snapshot.sheets)) for(const row of Object.values(sheet.cellData||{})) for(const cell of Object.values(row||{})) if(cell?.f) cell.f=normalizeFormula(cell.f);
  const {univer,univerAPI}=createUniver({locale:LocaleType.PT_BR,locales:{[LocaleType.PT_BR]:mergeLocales(coreLocale,filterLocale,sortLocale,validationLocale,conditionalLocale)},presets:[
    UniverSheetsCorePreset({menu:Object.fromEntries(['sheet.contextMenu.permission','sheet.command.add-range-protection-from-toolbar','sheet.command.add-range-protection-from-sheet-bar','sheet.command.view-sheet-permission-from-sheet-bar','sheet.command.delete-worksheet-protection-from-sheet-bar','sheet.command.change-sheet-protection-from-sheet-bar'].map(id=>[id,{hidden:true}])),container,header:true,toolbar:true,formulaBar:true,footer:true,ribbonType:'classic'}),
    UniverSheetsFilterPreset(),UniverSheetsSortPreset(),UniverSheetsDataValidationPreset(),UniverSheetsConditionalFormattingPreset(),
  ]});
  // Univer 1.2 submenu dispatch uses the menu ID instead of commandId for
  // clipboard entries. Route those IDs through the registered clipboard
  // commands, retaining the SDK's permissions, formats and paste target logic.
  const commands=univer.__getInjector().get(ICommandService);
  const clipboardCommands=['copy','cut','paste'].map(action=>commands.registerCommand({
    id:'sheet.command.'+action,type:CommandType.COMMAND,
    handler:async(_accessor,params)=>{
      if(readOnly&&action!=='copy')return false;
      try{return await univerAPI.executeCommand('univer.command.'+action,params);}
      catch(error){onError(error.name==='NotAllowedError'?'Permita o acesso à área de transferência no navegador ou use Ctrl+V para colar.':error.message);return false;}
    },
  }));
  const book=univerAPI.createWorkbook(snapshot);
  let nameBoxSelection=false,nameBoxTimer;
  const nameBoxKey=event=>{
    if(event.key==='Enter'&&event.target.closest?.('[data-u-comp="defined-name"]')){
      nameBoxSelection=true;clearTimeout(nameBoxTimer);
      nameBoxTimer=setTimeout(()=>{nameBoxSelection=false;},0);
    }
  };
  container.addEventListener('keydown',nameBoxKey,true);
  // Apply the same Portuguese aliases to native cell/formula-bar edits and
  // clipboard pastes as to the auxiliary input. Only formula fields change;
  // quoted text and literal cells beginning with '=' remain untouched.
  const commandSubscription=univerAPI.addEvent(univerAPI.Event.BeforeCommandExecute,event=>{
    if(event.params?.unitId!==book.getId())return;
    // The native name box omits the movement type. ONLY_SET changes the range
    // but leaves ribbon/selection observers on the previous cell in Univer 1.2.
    if(nameBoxSelection&&event.id==='sheet.operation.set-selections'&&event.params.type==null){event.params.type=SelectionMoveType.MOVE_END;nameBoxSelection=false;}
    if(event.id!=='sheet.mutation.set-range-values')return;
    for(const row of Object.values(event.params.cellValue||{}))for(const cell of Object.values(row||{}))if(typeof cell?.f==='string')cell.f=normalizeFormula(cell.f);
  });
  if(readOnly)container.inert=true;
  // Advertise readiness only after rendering. Apply read permissions after SDK
  // initialization so its defaults cannot replace the application's read role.
  if(univerAPI.getCurrentLifecycleStage()<3) await new Promise(resolve=>{
      const listener=univerAPI.addEvent(univerAPI.Event.LifeCycleChanged,({stage})=>{if(stage>=3){listener.dispose();resolve();}});
  });
  if(readOnly) {
    await book.getWorkbookPermission().setReadOnly();book.setEditable(false);
  }
  container.inert=false;
  let disposed=false,timer;
  const sync=()=>{
    if(disposed||readOnly) return;
    content.workbook=book.save();
    // Remove the redundant legacy matrices after migrating; old server versions
    // remain in history and are still understood by toWorkbook.
    delete content.cells;delete content.sheets;delete content.activeSheet;
  };
  const reportSelection=()=>{if(!disposed){const range=book.getActiveRange();if(range)onSelection(range.getA1Notation(),range.getFormulas()[0]?.[0]||(range.getRawValues()[0]?.[0]??''));}};
  const subscription=book.onCommandExecuted(command=>{
    if(disposed||command.type!==2)return;
    if(!readOnly&&!command.id.startsWith('formula.'))onChange();clearTimeout(timer);timer=setTimeout(()=>{try{sync();reportSelection();onRender();}catch(e){onError(e.message);}},50);
  });
  const selectionSubscription=book.onSelectionChange(reportSelection);
  return {
    quick(action,address){if(readOnly)return;const sheet=book.getActiveSheet(),range=sheet.getRange(address),pos=range.getRange();if(action==='row')sheet.insertRowsBefore(pos.startRow,1);else if(action==='column')sheet.insertColumnsBefore(pos.startColumn,1);else if(action==='clear')range.clear({contentsOnly:true});else throw Error('Ação inválida.');sync();onChange();},
    async flush(){await book.endEditingAsync(true);await univerAPI.getFormula().onCalculationResultApplied(10000);clearTimeout(timer);sync();},
    snapshot(){sync();return content.workbook;},
    dispose(){disposed=true;clearTimeout(timer);clearTimeout(nameBoxTimer);container.removeEventListener('keydown',nameBoxKey,true);subscription.dispose();selectionSubscription.dispose();commandSubscription.dispose();clipboardCommands.forEach(command=>command.dispose());univer.dispose();},
    select(address){const range=book.getActiveSheet().getRange(address);range.activate();return range;},
    set(address,value){if(readOnly)return;const range=book.getActiveSheet().getRange(address);range.setValue(typeof value==='string'&&value.startsWith('=')?normalizeFormula(value):value);range.activate();sync();onChange();},
    read(address){const range=book.getActiveSheet().getRange(address);return {values:range.getRawValues(),formulas:range.getFormulas()};},
    async paste(text,address){if(readOnly)return;const rows=text.includes('\t')?text.replace(/\r/g,'').replace(/\n$/,'').split('\n').map(r=>r.split('\t')):parseCSV(text,{maxRows:10000,maxCols:256,minCols:1});const anchor=book.getActiveSheet().getRange(address);const pos=anchor.getRange();const width=Math.max(...rows.map(r=>r.length));if(rows.length>10000||width>256||rows.length*width>50000)throw Error('Limite de colagem: 50 mil células, 10 mil linhas e 256 colunas.');const sheet=book.getActiveSheet();if(pos.startRow+rows.length>sheet.getMaxRows())sheet.insertRowsAfter(sheet.getMaxRows()-1,pos.startRow+rows.length-sheet.getMaxRows());if(pos.startColumn+width>sheet.getMaxColumns())sheet.insertColumnsAfter(sheet.getMaxColumns()-1,pos.startColumn+width-sheet.getMaxColumns());const values=rows.map(r=>Array.from({length:width},(_,i)=>r[i]??''));book.getActiveSheet().getRange(pos.startRow,pos.startColumn,rows.length,width).setValues(values);sync();onChange();},
    csv(){sync();return toCSV(workbookRows(content.workbook,book.getActiveSheet().getSheetId()));},
    rows(){sync();return workbookRows(content.workbook,book.getActiveSheet().getSheetId());},
    listSheets(){return book.getSheets().map(s=>({id:s.getSheetId(),name:s.getSheetName()}));},
    rangeRows(address,sheetId){const r=parsePivotRange(address),sheet=book.getSheetBySheetId(sheetId);if(!sheet)throw Error('A aba de origem foi removida. Configure outra fonte.');if(r.endRow>=sheet.getMaxRows()||r.endColumn>=sheet.getMaxColumns())throw Error('O intervalo ultrapassa o tamanho da aba.');return sheet.getRange(r.startRow,r.startColumn,r.height,r.width).getRawValues();},
    activeSheetId(){return book.getActiveSheet().getSheetId();},
    chartRows(address,sheetId){const sheet=book.getSheetBySheetId(sheetId);if(!sheet)throw Error('A aba de origem foi removida.');const range=sheet.getRange(address);const r=range.getRange();if(r.endRow-r.startRow>200||r.endColumn-r.startColumn!==1)throw Error('Selecione duas colunas, cabeçalho e até 200 linhas de dados.');return range.getRawValues();},
    api:univerAPI,
  };
}
