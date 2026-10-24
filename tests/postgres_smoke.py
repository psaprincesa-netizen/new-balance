"""Run only against a dedicated test database; creates isolated test accounts."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from server.database import PostgresStore
from server.workspace import Workspace, Conflict
from server.store import InvalidInput


def main():
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        raise SystemExit('TEST_DATABASE_URL é obrigatória; não use banco de produção.')
    store = PostgresStore(url)
    other_instance = PostgresStore(url, initialize=False)
    ws = Workspace(store)
    key = uuid.uuid4().hex
    email, other_email = f'{key}@example.org', f'other-{key}@example.org'
    a = store.register(email, 'Ana', 'senha-de-teste-longa')['id']
    b = other_instance.register(other_email, 'Bia', 'outra-senha-de-teste-longa')['id']
    item_id = None
    try:
        token = store.login(email, 'senha-de-teste-longa')
        assert other_instance.session_user(token)['id'] == a
        try:
            other_instance.register(email, 'Duplicada', 'senha-de-teste-longa')
            raise AssertionError('Duplicate email accepted')
        except InvalidInput:
            pass
        item = ws.create(a, {'kind':'document','title':'Teste PostgreSQL','content':{'text':'original'}})
        item_id = item['id']
        assert Workspace(other_instance).get(a,item_id)['content']['text'] == 'original'
        assert ws.list(b) == []
        ws.share(a,item_id,other_email,'read')
        assert Workspace(other_instance).get(b,item_id)['role'] == 'read'
        ws.share(a,item_id,other_email,'edit')
        def update(text):
            instance = Workspace(PostgresStore(url, initialize=False))
            try:
                return instance.update(a,item_id,{'title':'Teste PostgreSQL','content':{'text':text},'version':1})['version']
            except Conflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(update, ['um','dois']))
        assert outcomes.count('conflict') == 1, outcomes
        latest = ws.get(a,item_id)
        archived = ws.update(b,item_id,{'title':latest['title'],'content':latest['content'],'version':latest['version'],'deleted':True})
        assert archived['deleted']
        assert len(ws.history(a,item_id)) == 3
        ws.share(a,item_id,other_email,'remove')
        assert ws.list(b) == []
        for _ in range(20):
            assert store.auth_allowed(key)
        assert not other_instance.auth_allowed(key)
        store.logout(token)
        assert other_instance.session_user(token) is None
        print('PostgreSQL TLS verified: cross-instance persistence, authentication, duplicate constraints, sharing/revocation, real concurrency, history/trash, distributed rate limit, logout.')
    finally:
        with store.connect() as db:
            if item_id:
                db.execute('DELETE FROM versions WHERE item_id=?',(item_id,))
                db.execute('DELETE FROM shares WHERE item_id=?',(item_id,))
                db.execute('DELETE FROM items WHERE id=?',(item_id,))
            db.execute('DELETE FROM sessions WHERE user_id IN (?,?)',(a,b))
            db.execute('DELETE FROM users WHERE id IN (?,?)',(a,b))


if __name__ == '__main__':
    main()
