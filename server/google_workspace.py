"""Per-user Google OAuth with PKCE and encrypted refresh tokens."""
import base64,hashlib,json,os,re,secrets,time
from datetime import datetime,timezone
from email.message import EmailMessage
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from server.store import InvalidInput
from server.database import ConfigurationError
SCOPES='openid email https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.events'

def configured():return all(os.environ.get(key) for key in ('GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GOOGLE_TOKEN_ENCRYPTION_KEY'))
def redirect_uri():return os.environ.get('GOOGLE_REDIRECT_URI','https://new-balance-pi.vercel.app/google-callback.html')
def cipher():
    from cryptography.fernet import Fernet
    try:return Fernet(os.environ['GOOGLE_TOKEN_ENCRYPTION_KEY'].encode())
    except (KeyError,ValueError):raise ConfigurationError('Configure a chave de proteção da conexão Google no servidor.') from None

def request_json(url,data=None,token=None,form=False,method=None):
    headers={'Accept':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    if data is not None:headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
    payload=None if data is None else (urlencode(data).encode() if form else json.dumps(data).encode())
    try:
        with urlopen(Request(url,data=payload,headers=headers,method=method),timeout=15) as response:
            body=response.read(4_000_001)
            if len(body)>4_000_000:raise InvalidInput('A resposta do Google excede o limite. Refine a busca.')
            return json.loads(body) if body else {}
    except HTTPError as error:
        raise InvalidInput('O Google recusou a operação (HTTP '+str(error.code)+'). Confira a autorização e tente novamente.') from None
    except (URLError,TimeoutError,json.JSONDecodeError):raise InvalidInput('Não foi possível acessar o Google. Tente novamente.') from None

class GoogleWorkspace:
    def __init__(self,store):self.store=store
    def load(self,user):
        with self.store.connect() as db:row=db.execute('SELECT encrypted FROM google_connections WHERE user_id=?',(user,)).fetchone()
        if not row:return None
        from cryptography.fernet import InvalidToken
        try:return json.loads(cipher().decrypt(row['encrypted'].encode()))
        except (InvalidToken,ValueError):raise ConfigurationError('Não foi possível abrir a conexão Google. Reconecte a conta.') from None
    def save(self,user,data):
        encrypted=cipher().encrypt(json.dumps(data).encode()).decode()
        with self.store.connect() as db:db.execute('INSERT INTO google_connections VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET encrypted=excluded.encrypted',(user,encrypted))
    def status(self,user):
        ready=configured();data=self.load(user) if ready else None
        return {'configured':ready,'connected':bool(data),'email':data.get('email') if data else None}
    def start(self,user):
        if not configured():raise ConfigurationError('A integração está implementada. Configure o cliente OAuth Google e a chave de proteção nas variáveis da Vercel para autorizar sua conta.')
        state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48);now=int(time.time())
        with self.store.connect() as db:
            db.execute('DELETE FROM google_oauth_states WHERE expires<? OR user_id=?',(now,user))
            db.execute('INSERT INTO google_oauth_states VALUES (?,?,?,?)',(hashlib.sha256(state.encode()).hexdigest(),user,verifier,now+600))
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        return {'url':'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':os.environ['GOOGLE_CLIENT_ID'],'redirect_uri':redirect_uri(),'response_type':'code','scope':SCOPES,'state':state,'code_challenge':challenge,'code_challenge_method':'S256','access_type':'offline','prompt':'consent','include_granted_scopes':'true'})}
    def callback(self,user,data):
        state=data.get('state');code=data.get('code')
        if not isinstance(state,str) or len(state)>200 or not isinstance(code,str) or len(code)>4000:raise InvalidInput('Autorização inválida.')
        with self.store.connect() as db:row=db.execute('DELETE FROM google_oauth_states WHERE digest=? AND user_id=? AND expires>? RETURNING verifier',(hashlib.sha256(state.encode()).hexdigest(),user,int(time.time()))).fetchone()
        if not row:raise InvalidInput('A autorização expirou ou já foi usada. Conecte novamente.')
        token=request_json('https://oauth2.googleapis.com/token',{'grant_type':'authorization_code','code':code,'client_id':os.environ['GOOGLE_CLIENT_ID'],'client_secret':os.environ['GOOGLE_CLIENT_SECRET'],'redirect_uri':redirect_uri(),'code_verifier':row['verifier']},form=True)
        if not token.get('access_token') or not token.get('refresh_token'):raise InvalidInput('Autorize o acesso offline à conta Google para concluir.')
        required={scope for scope in SCOPES.split() if '/auth/' in scope}
        if not required.issubset(set(token.get('scope','').split())):raise InvalidInput('Autorize Gmail e Agenda na tela do Google para concluir a conexão.')
        profile=request_json('https://www.googleapis.com/oauth2/v2/userinfo',token=token['access_token'])
        stored={key:token[key] for key in ('access_token','refresh_token','scope') if key in token};stored.update(email=profile.get('email','Conta Google'),expires_at=time.time()+int(token.get('expires_in',3600)))
        self.save(user,stored);return {'connected':True,'email':stored['email']}
    def token(self,user):
        data=self.load(user)
        if not data:raise InvalidInput('Conecte sua conta Google primeiro.')
        if data.get('expires_at',0)<time.time()+60:
            renewed=request_json('https://oauth2.googleapis.com/token',{'grant_type':'refresh_token','refresh_token':data['refresh_token'],'client_id':os.environ['GOOGLE_CLIENT_ID'],'client_secret':os.environ['GOOGLE_CLIENT_SECRET']},form=True)
            data.update(access_token=renewed['access_token'],expires_at=time.time()+int(renewed.get('expires_in',3600)))
            if renewed.get('refresh_token'):data['refresh_token']=renewed['refresh_token']
            self.save(user,data)
        return data['access_token']
    def disconnect(self,user):
        data=self.load(user)
        with self.store.connect() as db:
            db.execute('DELETE FROM google_connections WHERE user_id=?',(user,));db.execute('DELETE FROM google_oauth_states WHERE user_id=?',(user,))
        if data:
            try:request_json('https://oauth2.googleapis.com/revoke',{'token':data['refresh_token']},form=True)
            except InvalidInput:pass
        return {'connected':False}
    def get(self,user,action,query):
        if action=='status':return self.status(user)
        token=self.token(user)
        if action=='messages':
            q=query.get('q',['in:inbox'])[0];page=query.get('page',[''])[0]
            if len(q)>500 or len(page)>1000:raise InvalidInput('Busca inválida.')
            params={'q':q,'maxResults':20}
            if page:params['pageToken']=page
            result=request_json('https://gmail.googleapis.com/gmail/v1/users/me/messages?'+urlencode(params),token=token)
            # Metadata only; full MIME is fetched on explicit opening.
            from concurrent.futures import ThreadPoolExecutor
            def metadata(message):
                return request_json('https://gmail.googleapis.com/gmail/v1/users/me/messages/'+message['id']+'?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date',token=token)
            with ThreadPoolExecutor(max_workers=4) as workers:messages=list(workers.map(metadata,result.get('messages',[])))
            return {'messages':messages,'nextPageToken':result.get('nextPageToken')}
        if action=='message':
            ident=query.get('id',[''])[0]
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',ident):raise InvalidInput('Mensagem inválida.')
            message=request_json('https://gmail.googleapis.com/gmail/v1/users/me/messages/'+ident+'?format=full',token=token)
            def text(part):
                if part.get('mimeType')=='text/plain' and part.get('body',{}).get('data'):
                    value=part['body']['data'];return base64.urlsafe_b64decode(value+'='*(-len(value)%4)).decode('utf-8',errors='replace')
                return '\n'.join(filter(None,(text(p) for p in part.get('parts',[]))))
            return {'id':message['id'],'threadId':message.get('threadId'),'headers':message.get('payload',{}).get('headers',[]),'text':text(message.get('payload',{})) or message.get('snippet','')}
        if action=='events':return request_json('https://www.googleapis.com/calendar/v3/calendars/primary/events?'+urlencode({'timeMin':datetime.now(timezone.utc).isoformat(),'maxResults':50,'singleEvents':'true','orderBy':'startTime'}),token=token)
        raise LookupError('Recurso Google não encontrado.')
    def post(self,user,action,data):
        if action=='connect':return self.start(user)
        if action=='callback':return self.callback(user,data)
        if action=='disconnect':return self.disconnect(user)
        token=self.token(user)
        if action=='send':
            to=data.get('to','');subject=data.get('subject','');body=data.get('body','')
            if not all(isinstance(v,str) for v in (to,subject,body)) or not re.fullmatch(r'[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+',to) or any(ch in subject+to for ch in '\r\n') or len(subject)>500 or len(body)>100000:raise InvalidInput('Informe destinatário, assunto e mensagem válidos.')
            message=EmailMessage();message['To']=to;message['Subject']=subject;message.set_content(body)
            raw=base64.urlsafe_b64encode(message.as_bytes()).decode()
            return request_json('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',{'raw':raw},token)
        if action in ('read','trash'):
            ident=data.get('id','')
            if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',ident):raise InvalidInput('Mensagem inválida.')
            return request_json('https://gmail.googleapis.com/gmail/v1/users/me/messages/'+ident+('/modify' if action=='read' else '/trash'),{'removeLabelIds':['UNREAD']} if action=='read' else {},token)
        if action=='event':
            title=data.get('title');start=data.get('start');end=data.get('end')
            if not isinstance(title,str) or not 1<=len(title)<=200:raise InvalidInput('Informe o título do evento.')
            try:
                a=datetime.fromisoformat(start.replace('Z','+00:00'));b=datetime.fromisoformat(end.replace('Z','+00:00'))
                if not a.tzinfo or not b.tzinfo or b<=a:raise ValueError()
            except (ValueError,AttributeError,TypeError):raise InvalidInput('Informe início e fim válidos com fuso horário.') from None
            payload={'summary':title,'start':{'dateTime':start},'end':{'dateTime':end}}
            if data.get('meet') is True:payload['conferenceData']={'createRequest':{'requestId':secrets.token_hex(16),'conferenceSolutionKey':{'type':'hangoutsMeet'}}}
            return request_json('https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1',payload,token)
        raise LookupError('Recurso Google não encontrado.')
