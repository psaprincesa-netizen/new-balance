import {detectPlatform,platformNames} from './install-platform.js';
let deferredInstall=null,installationReported=false,prompting=false;
const platform=detectPlatform(navigator);
const mode=window.matchMedia('(display-mode: standalone)');
const isStandalone=()=>mode.matches||navigator.standalone===true;
export const canInstall=()=>!!deferredInstall&&!prompting&&!isStandalone()&&!installationReported;
function updateInstallState(message){
  const button=document.querySelector('#install-now'),state=document.querySelector('#install-state'),installed=isStandalone()||installationReported;
  if(button){button.hidden=installed||!deferredInstall;button.disabled=prompting;}
  const help=document.querySelector('#install-help');if(help)help.hidden=installed;
  const text=installed?'O DRAP office está instalado ou aberto como aplicativo. Use o ícone de acesso criado no aparelho.':message||(deferredInstall?'A instalação está disponível. Confirme para criar o ícone do aplicativo.':'Escolha seu sistema abaixo para instalar e criar o atalho pelo navegador.');
  if(state)state.textContent=text;
  const feedback=document.querySelector('#install-feedback');if(feedback&&(message||installationReported)){feedback.textContent=text;feedback.hidden=false;clearTimeout(updateInstallState.timer);updateInstallState.timer=setTimeout(()=>{feedback.hidden=true;},9000);}
}
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();deferredInstall=event;updateInstallState();});
window.addEventListener('appinstalled',()=>{installationReported=true;deferredInstall=null;updateInstallState();});
mode.addEventListener?.('change',()=>updateInstallState());
export async function requestInstallation(){
  if(!canInstall())return false;
  const request=deferredInstall;deferredInstall=null;prompting=true;
  const button=document.querySelector('#install-now');if(button)button.disabled=true;
  try{
    await request.prompt();const choice=await request.userChoice;
    updateInstallState(choice.outcome==='accepted'?'Instalação solicitada. Conclua a confirmação para criar o ícone do aplicativo.':'Instalação cancelada. Você pode instalar e criar o atalho depois pelo menu do navegador.');
  }catch{updateInstallState('Não foi possível abrir a instalação. Use as instruções da página Instalar para criar o atalho.');}
  finally{prompting=false;if(installationReported)updateInstallState();}
  return true;
}
document.querySelector('#install-now')?.addEventListener('click',requestInstallation);
// If automatic installation is unavailable, the normal link opens instructions
// in another tab, preserving any unsaved work in the editor.
document.addEventListener('click',event=>{
  if(event.defaultPrevented||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
  if(event.target.closest?.('[data-install-action]')&&canInstall()){event.preventDefault();void requestInstallation();}
});
const detected=document.querySelector('#install-device');
if(detected)detected.textContent='Orientações para '+platformNames[platform];
const recommended=document.querySelector('[data-platform="'+platform+'"]');
if(recommended){recommended.dataset.recommended='true';const help=document.querySelector('#install-help');if(help)help.href='#'+recommended.id;}
const link=document.querySelector('#install-url');if(link)link.value=location.origin+'/install';
document.querySelector('#copy-install-link')?.addEventListener('click',async()=>{
  try{await navigator.clipboard.writeText(link.value);document.querySelector('#share-install-status').textContent='Link copiado. Abra-o no aparelho em que deseja instalar.';}
  catch{link.focus();link.select();document.querySelector('#share-install-status').textContent='Selecione e copie o endereço exibido acima.';}
});
const share=document.querySelector('#share-install-link');
if(share&&navigator.share){share.hidden=false;share.addEventListener('click',async()=>{try{await navigator.share({title:'Instalar DRAP office',url:link.value});}catch(error){if(error.name!=='AbortError')document.querySelector('#share-install-status').textContent='Use Copiar link para compartilhar o endereço.';}});}
function connectivity(){
  const banner=document.querySelector('#connection-status');
  if(banner){banner.hidden=navigator.onLine;banner.textContent=navigator.onLine?'':'Sem conexão. Mantenha esta janela aberta e salve suas alterações quando a internet voltar.';}
}
window.addEventListener('online',connectivity);window.addEventListener('offline',connectivity);connectivity();updateInstallState();
if('serviceWorker' in navigator&&window.isSecureContext){
  navigator.serviceWorker.register('/service-worker.js',{scope:'/',updateViaCache:'none'}).catch(()=>{
    if(!deferredInstall&&!isStandalone())updateInstallState('Siga as instruções abaixo. A instalação automática não ficou disponível neste navegador.');
  });
}
