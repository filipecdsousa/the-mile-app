import io
import json
import os
import tempfile
import unittest
from urllib.parse import urlparse, parse_qs

temp = tempfile.TemporaryDirectory()
os.environ['MILE_DATA_DIR'] = temp.name
import app

PDF = b'%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n'

class Client:
    def __init__(self):
        self.cookie=''
        self.csrf=''
    def request(self,path,method='GET',body=None,csrf=True,origin=None):
        parsed=urlparse(path)
        blob=body if isinstance(body,bytes) else json.dumps(body or {}).encode()
        env={'REQUEST_METHOD':method,'PATH_INFO':parsed.path,'QUERY_STRING':parsed.query,'wsgi.input':io.BytesIO(blob),'CONTENT_LENGTH':str(len(blob)), 'HTTP_COOKIE':self.cookie,'REMOTE_ADDR':'127.0.0.1'}
        if csrf:env['HTTP_X_CSRF_TOKEN']=self.csrf
        if origin:env['HTTP_ORIGIN']=origin
        result={}
        def start(status,headers):
            result['status']=int(status.split()[0]);result['headers']=dict(headers)
        out=b''.join(app.application(env,start))
        if 'Set-Cookie' in result['headers']:self.cookie=result['headers']['Set-Cookie'].split(';')[0]
        result['body']=json.loads(out) if result['headers']['Content-Type'].startswith('application/json') else out
        if path=='/api/me' and result['status']==200:self.csrf=result['body']['csrf'] or ''
        return result
    def activate(self,link):
        token=parse_qs(urlparse(link).query)['activate'][0]
        result=self.request('/api/activate','POST',{'token':token,'password':'private-password-123'})
        self.request('/api/me')
        return result

class PortalTest(unittest.TestCase):
    def setUp(self):
        for p in app.DATA.glob('pdfs/*'):p.unlink()
        db=app.DATA/'mile.sqlite3'
        db.unlink(missing_ok=True)
        app.initialize()
        self.admin=Client()
        with app.connect() as c:
            uid=c.execute('SELECT id FROM users WHERE email=?',('filipesousa@themile.pt',)).fetchone()['id']
            self.link=app.activation(c,uid)
        self.assertEqual(self.admin.activate(self.link)['status'],200)
    def player(self,name,email):
        r=self.admin.request('/api/players','POST',{'name':name,'email':email})
        self.assertEqual(r['status'],201)
        client=Client();self.assertEqual(client.activate(r['body']['activation_url'])['status'],200)
        return client,client.request('/api/me')['body']['user']['id']
    def upload(self,uid,pdf=PDF):
        return self.admin.request('/api/documents?player='+uid+'&folder=nutrition&title=Plan.pdf','POST',pdf)
    def test_admin_seed_and_no_shared_password(self):
        with app.connect() as c:
            rows=c.execute("SELECT email,password FROM users WHERE role='admin'").fetchall()
        self.assertEqual(len(rows),2)
        self.assertIsNone(next(r['password'] for r in rows if r['email']=='raquelgomes@themile.pt'))
    def test_cross_player_access_and_session_boundaries(self):
        p1,id1=self.player('One','one@example.com');p2,id2=self.player('Two','two@example.com')
        document=self.upload(id1)['body']['id']
        self.assertEqual(p1.request('/api/documents/'+document)['body'],PDF)
        self.assertEqual(p2.request('/api/documents/'+document)['status'],403)
        self.assertEqual(p2.request('/api/documents?player='+id1)['status'],403)
        self.assertEqual(Client().request('/api/documents/'+document)['status'],401)
        self.assertEqual(p1.request('/api/players')['status'],403)
        self.assertEqual(p1.request('/api/documents/'+document,'DELETE',{})['status'],403)
        self.assertEqual(p1.request('/api/documents?player='+id1+'&folder=other&title=x.pdf','POST',PDF)['status'],403)
        self.assertEqual(p2.request('/api/documents')['body']['documents'],[])
    def test_csrf_and_origin(self):
        self.assertEqual(self.admin.request('/api/players','POST',{'name':'X','email':'x@example.com'},csrf=False)['status'],403)
        self.assertEqual(self.admin.request('/api/players','POST',{},origin='https://evil.example')['status'],403)
    def test_replace_delete_and_pdf_validation(self):
        p,uid=self.player('One','one@example.com')
        self.assertEqual(self.upload(uid,b'not a PDF')['status'],400)
        did=self.upload(uid)['body']['id']
        updated=PDF+b'\n'
        self.assertEqual(self.admin.request('/api/documents/'+did,'PUT',updated)['status'],200)
        self.assertEqual(p.request('/api/documents/'+did)['body'],updated)
        self.assertEqual(self.admin.request('/api/documents/'+did,'DELETE',{})['status'],200)
        self.assertEqual(p.request('/api/documents/'+did)['status'],404)
    def test_deactivation_revokes_session(self):
        p,uid=self.player('One','one@example.com')
        self.assertEqual(self.admin.request('/api/players/'+uid+'/status','POST',{'active':False})['status'],200)
        self.assertEqual(p.request('/api/documents')['status'],401)
    def test_single_use_activation_and_password_reset(self):
        p,uid=self.player('One','one@example.com')
        link=self.admin.request('/api/players/'+uid+'/activation','POST',{})['body']['activation_url']
        new=Client();self.assertEqual(new.activate(link)['status'],200)
        self.assertEqual(p.request('/api/documents')['status'],401)
        self.assertEqual(Client().activate(link)['status'],400)
    def test_expired_activation_and_rate_limit(self):
        r=self.admin.request('/api/players','POST',{'name':'One','email':'one@example.com'})
        with app.connect() as c:c.execute('UPDATE activations SET expires=0')
        self.assertEqual(Client().activate(r['body']['activation_url'])['status'],400)
        client=Client()
        for i in range(10):self.assertEqual(client.request('/api/login','POST',{'email':'unknown@example.com','password':'invalid-password'})['status'],401)
        self.assertEqual(client.request('/api/login','POST',{'email':'unknown@example.com','password':'invalid-password'})['status'],429)
    def test_no_data_files_served_and_session_security_headers(self):
        self.assertEqual(Client().request('/data/mile.sqlite3')['status'],404)
        self.assertEqual(Client().request('/logo.png')['status'],200)
        r=self.admin.request('/api/me')
        self.assertEqual(r['headers']['Cache-Control'],'no-store')
        self.assertEqual(r['headers']['X-Frame-Options'],'DENY')

if __name__=='__main__':unittest.main()
