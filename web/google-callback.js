const query=new URLSearchParams(location.search),status=document.querySelector('#google-callback-status');
history.replaceState(null,'','/google-callback.html');
try{
  if(query.has('error'))throw Error('A autorização Google foi cancelada.');
  const response=await fetch('/api/google/callback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:query.get('code'),state:query.get('state')})}),data=await response.json();
  if(!response.ok)throw Error(data.error||'Não foi possível conectar.');
  location.replace('/?google=connected');
}catch(error){status.textContent=error.message;}
