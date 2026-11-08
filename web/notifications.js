export async function mountNotifications(root,{api,esc,notify,openComment,onUnread}){
  const token={};root.notificationToken=token;let offset=0,request=0;
  const active=()=>root.isConnected&&root.notificationToken===token;
  async function load(next=offset){
    if(!active())return;const sequence=++request;root.setAttribute('aria-busy','true');
    try{const data=await api('/api/notifications?offset='+next);if(!active()||sequence!==request)return;offset=next;onUnread(data.unread);
      root.innerHTML=`<div class="row between"><h2>Menções em comentários</h2><div class="row"><button id="notifications-refresh">Atualizar notificações</button><button id="notifications-read-all" ${data.unread?'':'disabled'}>Marcar todas como lidas</button></div></div><p role="status">${data.unread} não lida(s). As notificações mostram apenas arquivos ativos aos quais você tem acesso.</p><p id="notification-error" class="error" role="alert"></p><div class="stack">${data.items.map(n=>`<article class="card notification-card" data-notification="${esc(n.id)}"><h3>${esc(n.item_title)}</h3><span class="badge">${n.read_at?'Lida':'Não lida'}</span><p>${esc(n.actor)} mencionou você em um comentário.</p><blockquote class="comment-text">${esc(n.preview)}${n.preview_truncated?'…':''}</blockquote><small>${esc(new Date(n.created).toLocaleString('pt-BR'))}</small><div class="row"><button data-notification-open="${esc(n.id)}">Ver comentário</button><button data-notification-read="${esc(n.id)}">${n.read_at?'Marcar como não lida':'Marcar como lida'}</button><button data-notification-dismiss="${esc(n.id)}">Excluir notificação</button></div></article>`).join('')||'<p>Nenhuma notificação disponível.</p>'}</div><div class="row">${offset?'<button id="notifications-prev">Notificações anteriores</button>':''}${data.next_offset!==null?'<button id="notifications-next">Próximas notificações</button>':''}</div>`;
      const action=(button,task)=>async()=>{button.disabled=true;try{await task();}catch(error){if(active())root.querySelector('#notification-error').textContent=error.message;notify(error.message);}finally{if(button.isConnected)button.disabled=false;}};
      root.querySelector('#notifications-refresh').onclick=()=>load();
      const all=root.querySelector('#notifications-read-all');all.onclick=action(all,async()=>{await api('/api/notifications/read',{all:true});await load();});
      root.querySelectorAll('[data-notification-open]').forEach(button=>button.onclick=action(button,async()=>{const item=data.items.find(n=>n.id===button.dataset.notificationOpen);await api('/api/notifications/read',{id:item.id,read:true});if(!active())return;onUnread(Math.max(0,data.unread-(item.read_at?0:1)));await openComment(item.item_id,item.comment_id);}));
      root.querySelectorAll('[data-notification-read]').forEach(button=>button.onclick=action(button,async()=>{const item=data.items.find(n=>n.id===button.dataset.notificationRead);await api('/api/notifications/read',{id:item.id,read:!item.read_at});await load();}));
      root.querySelectorAll('[data-notification-dismiss]').forEach(button=>button.onclick=action(button,async()=>{await api('/api/notifications/dismiss',{id:button.dataset.notificationDismiss});await load();}));
      root.querySelector('#notifications-prev')?.addEventListener('click',()=>load(Math.max(0,offset-50)));
      root.querySelector('#notifications-next')?.addEventListener('click',()=>load(data.next_offset));
    }catch(error){if(active()&&sequence===request){root.innerHTML=`<p role="alert">${esc(error.message)}</p><button id="notifications-retry">Tentar carregar notificações novamente</button>`;root.querySelector('button').onclick=()=>load();notify(error.message);}}
    finally{if(active()&&sequence===request)root.removeAttribute('aria-busy');}
  }
  root.innerHTML='<p role="status">Carregando notificações…</p>';await load();
}
