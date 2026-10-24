import tempfile
import unittest
from pathlib import Path
from server.store import Store
from server.workspace import Workspace
from scripts.backup import snapshot


class BackupTest(unittest.TestCase):
    def test_restore_into_new_database_and_preserve_existing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, backup, restored = [root / n for n in ('source.db','backup.db','restored.db')]
            store = Store(source)
            user = store.register('ana@example.org','Ana','senha-de-teste-longa')['id']
            item = Workspace(store).create(user, {'kind':'document','title':'Contrato','content':{'text':'preservado'}})
            snapshot(source, backup)
            snapshot(backup, restored)
            recovered = Store(restored)
            self.assertIsNotNone(recovered.login('ana@example.org','senha-de-teste-longa'))
            self.assertEqual(Workspace(recovered).get(user,item['id'])['content']['text'],'preservado')
            with self.assertRaises(FileExistsError):
                snapshot(source, backup)
