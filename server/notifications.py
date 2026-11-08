"""Explicit comment mentions and an access-filtered private notification inbox."""
import secrets,time
from server.store import InvalidInput

ACCESS=""" FROM notifications n JOIN items i ON i.id=n.item_id
 LEFT JOIN shares s ON s.item_id=i.id AND s.user_id=n.user_id
 WHERE n.user_id=? AND i.deleted=0 AND (i.owner=n.user_id OR s.user_id=n.user_id)"""

def add_mentions(workspace,db,actor,item_id,comment_id,emails,created):
    if not isinstance(emails,list) or len(emails)>10 or any(not isinstance(e,str) or not e.strip() or len(e)>254 for e in emails):
        raise InvalidInput('Mencione até 10 e-mails de pessoas que já têm acesso ao arquivo.')
    people=[]
    for email in sorted(set(e.strip().lower() for e in emails)):
        person=db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
        if not person or not workspace.accessible(db,person['id'],item_id):
            raise InvalidInput('Só é possível mencionar pessoas que já têm acesso ao arquivo.')
        people.append(person['id'])
    for ident in people:
        db.execute('INSERT INTO comment_mentions(comment_id,user_id) VALUES (?,?)',(comment_id,ident))
        if ident!=actor:
            db.execute('''INSERT INTO notifications(id,user_id,item_id,comment_id,actor_id,created,read_at)
              VALUES (?,?,?,?,?,?,0)''',(secrets.token_hex(16),ident,item_id,comment_id,actor,created))

def unread(db,user):
    return db.execute('SELECT COUNT(*) AS n'+ACCESS+' AND n.read_at=0',(user,)).fetchone()['n']

def count(workspace,user):
    with workspace.store.connect() as db:return {'unread':unread(db,user)}

def listing(workspace,user,offset=0):
    with workspace.store.connect() as db:
        rows=db.execute('''SELECT n.id,n.item_id,n.comment_id,n.created,n.read_at,i.title AS item_title,
          u.name AS actor, c.body
          FROM notifications n JOIN items i ON i.id=n.item_id JOIN comments c ON c.id=n.comment_id
          JOIN users u ON u.id=n.actor_id LEFT JOIN shares s ON s.item_id=i.id AND s.user_id=n.user_id
          WHERE n.user_id=? AND i.deleted=0 AND (i.owner=n.user_id OR s.user_id=n.user_id)
          ORDER BY n.created DESC,n.id DESC LIMIT 50 OFFSET ?''',(user,offset)).fetchall()
        items=[]
        for row in rows:
            item=dict(row);body=item.pop('body');item['preview']=body[:240];item['preview_truncated']=len(body)>240;items.append(item)
        return {'items':items,'next_offset':offset+50 if len(items)==50 else None,'unread':unread(db,user)}

def update(workspace,user,data,dismiss=False):
    now=time.time_ns()//1000000
    if isinstance(data,dict) and set(data)=={'all'} and data['all'] is True and not dismiss:
        with workspace.store.connect() as db:
            db.execute('''UPDATE notifications SET read_at=? WHERE user_id=? AND read_at=0 AND id IN
              (SELECT n.id'''+ACCESS+')',(now,user,user))
        return {'ok':True}
    if (not isinstance(data,dict) or set(data)!=({'id'} if dismiss else {'id','read'})
        or not isinstance(data.get('id'),str) or not 1<=len(data['id'])<=100 or (not dismiss and type(data.get('read')) is not bool)):
        raise InvalidInput('Notificação ou estado inválidos.')
    with workspace.store.connect() as db:
        row=db.execute('SELECT n.id'+ACCESS+' AND n.id=?',(user,data['id'])).fetchone()
        if not row:raise LookupError('Notificação indisponível.')
        if dismiss:db.execute('DELETE FROM notifications WHERE id=? AND user_id=?',(data['id'],user))
        else:db.execute('UPDATE notifications SET read_at=? WHERE id=? AND user_id=?',(now if data['read'] else 0,data['id'],user))
    return {'ok':True}
