import io,json,tempfile,unittest,zipfile
from http.client import HTTPConnection
from pathlib import Path
from PIL import Image
from tests import test_api
from scripts.package_release import package

class InstallTest(unittest.TestCase):
    setUp=test_api.ApiTest.setUp
    tearDown=test_api.ApiTest.tearDown
    def get(self,path):
        connection=HTTPConnection('127.0.0.1',self.server.server_port);connection.request('GET',path);r=connection.getresponse();result=(r.status,dict(r.getheaders()),r.read());connection.close();return result
    def test_public_install_assets_manifest_and_icons(self):
        for path,mime in [('/install','text/html'),('/install/','text/html'),('/pwa.js','javascript'),('/install-platform.js','javascript'),('/install.css','text/css'),('/offline.html','text/html'),('/service-worker.js','javascript')]:
            status,headers,body=self.get(path);self.assertEqual(status,200,path);self.assertIn(mime,headers['Content-Type']);self.assertTrue(body)
        status,headers,body=self.get('/manifest.webmanifest');self.assertEqual(status,200);self.assertIn('manifest+json',headers['Content-Type'])
        manifest=json.loads(body);self.assertEqual(manifest['id'],'/');self.assertEqual(manifest['start_url'],'/');self.assertEqual(manifest['scope'],'/');self.assertEqual(manifest['display'],'standalone');self.assertFalse(manifest['prefer_related_applications'])
        for icon in manifest['icons']:
            status,headers,body=self.get(icon['src']);self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],'image/png');image=Image.open(io.BytesIO(body));self.assertEqual(image.size,tuple(map(int,icon['sizes'].split('x'))))
        self.assertEqual(Image.open(io.BytesIO(self.get('/icons/apple-touch-icon.png')[2])).size,(180,180))
        self.assertEqual(self.get('/icons/../../.env')[0],404)
    def test_download_package_contains_installation_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=package(Path(tmp)/'source.zip')
            with zipfile.ZipFile(archive) as z:
                for name in ['web/manifest.webmanifest','web/service-worker.js','web/install.html','web/pwa.js','web/icons/icon-192.png','web/icons/icon-512.png','web/icons/maskable-512.png','web/icons/apple-touch-icon.png','scripts/build-pwa.mjs']:
                    self.assertIn('drap-office/'+name,z.namelist())
