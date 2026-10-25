import {Editor,Extension} from '@tiptap/core';
import {Plugin} from '@tiptap/pm/state';
import StarterKit from '@tiptap/starter-kit';
import {Markdown} from '@tiptap/markdown';
import Image from '@tiptap/extension-image';
import {TableKit} from '@tiptap/extension-table';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
export function mountDocument(element,content,{readOnly=false,onChange,notify,onState=()=>{}}){
  const LocalImage=Image.extend({
    parseMarkdown(token,helpers){const id=String(token.href||'').replace(/^drap-image:/,''),im=content.images?.find(im=>im.id===id);return helpers.createNode('image',{src:token.href,alt:im?.alt||token.text,width:im?.width||null});},
    parseHTML(){return [{tag:'img[data-drap-image]',getAttrs:el=>content.images?.some(im=>im.id===el.dataset.drapImage)?{src:'drap-image:'+el.dataset.drapImage}:false}];},
    renderHTML({node}){const id=String(node.attrs.src||'').replace(/^drap-image:/,''),im=content.images?.find(im=>im.id===id);return im?['img',{src:im.src,alt:im.alt||node.attrs.alt||'', 'data-drap-image':id,style:`width:${im.width||80}%;max-width:100%;max-height:900px;object-fit:contain`}]:['span',{},'Imagem indisponível'];},
  });
  // Markdown tables require one header row. Promote the first remaining row
  // after deleting a header so serialization never inserts a phantom row.
  const TableHeaders=Extension.create({name:'persistentTableHeader',addProseMirrorPlugins(){return [new Plugin({appendTransaction(transactions,oldState,state){if(!transactions.some(t=>t.docChanged))return null;const tr=state.tr;let changed=false;state.doc.descendants((node,pos)=>{if(node.type.name!=='table'||!node.firstChild)return;let offset=0;node.firstChild.forEach(cell=>{if(cell.type.name!=='tableHeader'){tr.setNodeMarkup(pos+2+offset,state.schema.nodes.tableHeader,cell.attrs);changed=true;}offset+=cell.nodeSize;});});return changed?tr:null;}})];}});
  let editor;
  const words=instance=>{const text=instance.getText().trim();return text?text.split(/\s+/).length:0;};
  const state=instance=>({table:instance.isActive('table'),undo:instance.can().undo(),redo:instance.can().redo()});
  function pasteText(text){if(!text)return;editor.commands.insertContent(text.replace(/\r/g,'').split('\n').map(line=>({type:'paragraph',content:line?[{type:'text',text:line}]:[]})));}
  editor=new Editor({element,extensions:[StarterKit.configure({heading:{levels:[1,2,3]},underline:false,strike:false,horizontalRule:false,link:{openOnClick:readOnly,autolink:false,isAllowedUri:url=>/^https?:\/\//i.test(url)}}),Markdown,LocalImage,TableHeaders,TableKit.configure({table:{resizable:false}}),TaskList,TaskItem.configure({nested:false})],content:content.text,contentType:'markdown',editable:!readOnly,injectCSS:false,
    editorProps:{attributes:{class:'visual-document',role:'textbox','aria-label':'Página do documento','aria-multiline':'true','aria-readonly':String(readOnly)},handlePaste(view,event){if(readOnly)return true;event.preventDefault();if(event.clipboardData.files.length)notify('Use Inserir imagem para adicionar arquivos.');else pasteText(event.clipboardData.getData('text/plain'));return true;},handleDrop(view,event){if(readOnly)return true;if(view.dragging)return false;event.preventDefault();pasteText(event.dataTransfer.getData('text/plain'));return true;}},
    onUpdate:({editor:instance})=>{if(!readOnly)onChange(instance.getMarkdown(),words(instance));onState(state(instance));},onSelectionUpdate:({editor:instance})=>onState(state(instance)),
  });
  const commands={'# ':chain=>chain.toggleHeading({level:1}),'## ':chain=>chain.toggleHeading({level:2}),'**':chain=>chain.toggleBold(),'*':chain=>chain.toggleItalic(),'- ':chain=>chain.toggleBulletList(),'- [ ] ':chain=>chain.toggleTaskList(),paragraph:chain=>chain.setParagraph(),undo:chain=>chain.undo(),redo:chain=>chain.redo(),row:chain=>chain.addRowAfter(),column:chain=>chain.addColumnAfter(),deleteRow:chain=>chain.deleteRow(),deleteColumn:chain=>chain.deleteColumn(),deleteTable:chain=>chain.deleteTable()};
  return {
    replace(search,replacement){
      if(readOnly||!search)return 0;const matches=[];
      editor.state.doc.descendants((node,pos)=>{if(!node.isTextblock)return;let text='';node.forEach(child=>{text+=child.isText?child.text:'\uFFFC'.repeat(child.nodeSize);});let at=0;while((at=text.indexOf(search,at))!==-1){matches.push({from:pos+1+at,to:pos+1+at+search.length});at+=search.length;}});
      if(matches.length){const tr=editor.state.tr;for(const match of matches.reverse())tr.insertText(replacement,match.from,match.to);editor.view.dispatch(tr);}
      return matches.length;
    },
    dispose(){editor.destroy();},
    state(){return state(editor);},
    html(){return editor.getHTML();},
    words(){return words(editor);},
    refresh(){editor.commands.setContent(content.text,{contentType:'markdown',emitUpdate:false});},
    format(key){if(readOnly)return;commands[key]?.(editor.chain().focus()).run();},
    insert(text){if(readOnly)return;const {$from}=editor.state.selection;for(let depth=$from.depth;depth>0;depth--){if($from.node(depth).type.name==='table'){if(text.trim().startsWith('![')){editor.chain().focus().insertContentAt($from.after(depth),text,{contentType:'markdown'}).run();return;}if(text.includes('| ---')){notify('Insira a nova tabela fora da tabela atual.');return;}}}editor.chain().focus().insertContent(text,{contentType:'markdown'}).run();},
  };
}
