"""The Mile private document portal. WSGI; standard-library application."""
import base64
import hashlib
import hmac
import json
import logging
import mimetypes
import os
import secrets
import sqlite3
try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None
import time
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('MILE_DATA_DIR', ROOT / 'data')).resolve()
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
BASE_URL = os.environ.get('MILE_BASE_URL', 'http://localhost:8000').strip().rstrip('/')
ALLOWED_ORIGINS = {BASE_URL, 'https://the-mile-app.onrender.com'}
ALLOWED_ORIGIN_HOSTS = {h for h in (urlparse(x).hostname for x in ALLOWED_ORIGINS) if h}
ALLOWED_ORIGIN_HOSTS.update({'app.themile.pt', 'the-mile-app.onrender.com'})
SECURE = BASE_URL.startswith('https://')
MAX_PDF = 20 * 1024 * 1024
FOLDERS = ('nutrition', 'menus', 'other')
ADMINS = (('Filipe Sousa', 'filipesousa@themile.pt'), ('Raquel Gomes', 'raquelgomes@themile.pt'))

def connect():
    if DATABASE_URL:
        if psycopg is None:
            raise RuntimeError('DATABASE_URL is set but psycopg is not installed')
        return PgConnection(psycopg.connect(DATABASE_URL, row_factory=dict_row))
    c = sqlite3.connect(DATA / 'mile.sqlite3', timeout=20)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys = ON')
    return c

class PgCursor:
    def __init__(self, cursor):
        self.cursor = cursor
    def fetchone(self):
        return self.cursor.fetchone()
    def fetchall(self):
        return self.cursor.fetchall()

class PgConnection:
    def __init__(self, conn):
        self.conn = conn
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()
    def execute(self, sql, params=()):
        sql = sql.replace('?', '%s')
        if sql.startswith('INSERT OR IGNORE INTO users'):
            sql = sql.replace('INSERT OR IGNORE INTO users', 'INSERT INTO users', 1) + ' ON CONFLICT (email) DO NOTHING'
        elif sql.startswith('INSERT OR REPLACE INTO attempts'):
            sql = 'INSERT INTO attempts(key,count,until_time) VALUES(%s,%s,%s) ON CONFLICT (key) DO UPDATE SET count=EXCLUDED.count, until_time=EXCLUDED.until_time'
        return PgCursor(self.conn.execute(sql, params))
    def executescript(self, script):
        self.conn.execute(script)
    def commit(self):
        self.conn.commit()

def initialize():
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    with connect() as c:
        if DATABASE_URL:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','player')), password TEXT, active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires BIGINT NOT NULL);
            CREATE TABLE IF NOT EXISTS activations(token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires BIGINT NOT NULL);
            CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), folder TEXT NOT NULL, title TEXT NOT NULL, size BIGINT NOT NULL, updated BIGINT NOT NULL, uploaded_by TEXT NOT NULL REFERENCES users(id), data BYTEA NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY, count INTEGER NOT NULL, until_time BIGINT NOT NULL);
            ''')
        else:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','player')), password TEXT, active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS activations(token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), folder TEXT NOT NULL, title TEXT NOT NULL, size INTEGER NOT NULL, updated INTEGER NOT NULL, uploaded_by TEXT NOT NULL REFERENCES users(id), data BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY, count INTEGER NOT NULL, until_time INTEGER NOT NULL);
            ''')
        for name, email in ADMINS:
            c.execute('INSERT OR IGNORE INTO users(id,name,email,role) VALUES(?,?,?,?)', (secrets.token_hex(16), name, email, 'admin'))

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def password_hash(value):
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(value.encode(), salt=salt, n=16384, r=8, p=1)
    return salt.hex() + ':' + key.hex()

def password_valid(value, stored):
    if not stored:
        # Preserve comparable work for an unknown or unactivated account.
        hashlib.scrypt(value.encode(), salt=b'\0' * 16, n=16384, r=8, p=1)
        return False
    salt, key = stored.split(':')
    actual = hashlib.scrypt(value.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, key)

def activation(c, user_id):
    token = secrets.token_urlsafe(32)
    c.execute('DELETE FROM activations WHERE user_id=?', (user_id,))
    c.execute('INSERT INTO activations VALUES(?,?,?)', (digest(token), user_id, int(time.time()) + 86400))
    return BASE_URL + '/?activate=' + quote(token)

class Problem(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code

def application(env, start_response):
    headers = [('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'), ('X-Frame-Options', 'DENY'), ('Referrer-Policy', 'no-referrer'), ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")]
    if SECURE:
        headers.append(('Strict-Transport-Security', 'max-age=31536000'))
    def respond(status, data, mime='application/json; charset=utf-8'):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode()
        headers.extend([('Content-Type', mime), ('Content-Length', str(len(data)))])
        start_response(f'{status} ' + {200:'OK', 201:'Created', 400:'Bad Request', 401:'Unauthorized', 403:'Forbidden', 404:'Not Found', 409:'Conflict', 413:'Payload Too Large', 429:'Too Many Requests', 500:'Internal Server Error'}.get(status, 'Error'), headers)
        return [data]
    try:
        method = env.get('REQUEST_METHOD', 'GET')
        path = env.get('PATH_INFO', '/')
        static_files = {
            '/': 'index.html',
            '/app.js': 'app.js',
            '/style.css': 'style.css',
            '/logo.png': 'logo.png',
            '/manifest.webmanifest': 'manifest.webmanifest',
            '/sw.js': 'sw.js',
            '/icon-192.png': 'icon-192.png',
            '/icon-512.png': 'icon-512.png',
            '/apple-touch-icon.png': 'apple-touch-icon.png',
        }
        if method == 'GET' and path in static_files:
            file = ROOT / 'static' / static_files[path]
            mime = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
            if file.name.endswith('.webmanifest'):
                mime = 'application/manifest+json'
            return respond(200, file.read_bytes(), mime)
        if not path.startswith('/api/'):
            raise Problem(404, 'not_found')
        cookies = SimpleCookie()
        try:
            cookies.load(env.get('HTTP_COOKIE', ''))
        except Exception:
            pass
        token = cookies['mile_session'].value if 'mile_session' in cookies else ''
        with connect() as c:
            now = int(time.time())
            user = c.execute('SELECT u.*,s.csrf FROM sessions s JOIN users u ON s.user_id=u.id WHERE s.token=? AND s.expires>? AND u.active=1', (digest(token), now)).fetchone()
            if method != 'GET':
                origin = (env.get('HTTP_ORIGIN') or '').strip().rstrip('/')
                if origin:
                    parsed_origin = urlparse(origin)
                    origin_host = (parsed_origin.hostname or '').lower()
                    if parsed_origin.scheme not in ('https', 'http') or origin_host not in ALLOWED_ORIGIN_HOSTS:
                        logging.warning('Blocked origin: %r (host=%r, allowed=%r)', origin, origin_host, sorted(ALLOWED_ORIGIN_HOSTS))
                        raise Problem(403, 'origin')
                if user and not hmac.compare_digest(env.get('HTTP_X_CSRF_TOKEN', ''), user['csrf']):
                    raise Problem(403, 'csrf')
            if path == '/api/me' and method == 'GET':
                return respond(200, {'user': dict(id=user['id'], name=user['name'], email=user['email'], role=user['role']) if user else None, 'csrf': user['csrf'] if user else None})
            if path in ('/api/login', '/api/activate') and method == 'POST':
                body = read_json(env)
                limit_key = digest(env.get('REMOTE_ADDR', '') + ':' + path)
                rate_limit(c, limit_key, now)
                password = body.get('password', '')
                if not isinstance(password, str) or len(password) > 256:
                    raise Problem(400, 'password')
                if path == '/api/login':
                    email = str(body.get('email', '')).strip().lower()
                    u = c.execute('SELECT * FROM users WHERE email=? AND active=1', (email,)).fetchone()
                    if not password_valid(password, u['password'] if u else None):
                        raise Problem(401, 'credentials')
                else:
                    if len(password) < 12:
                        raise Problem(400, 'password_length')
                    a = c.execute('SELECT u.* FROM activations a JOIN users u ON u.id=a.user_id WHERE a.token=? AND a.expires>? AND u.active=1', (digest(str(body.get('token',''))), now)).fetchone()
                    if not a:
                        raise Problem(400, 'activation')
                    c.execute('UPDATE users SET password=? WHERE id=?', (password_hash(password), a['id']))
                    c.execute('DELETE FROM activations WHERE user_id=?', (a['id'],))
                    c.execute('DELETE FROM sessions WHERE user_id=?', (a['id'],))
                    u = a
                session_token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
                c.execute('DELETE FROM sessions WHERE expires<=?', (now,))
                c.execute('INSERT INTO sessions VALUES(?,?,?,?)', (digest(session_token), u['id'], csrf, now + 43200))
                c.execute('DELETE FROM attempts WHERE key=?', (limit_key,))
                c.commit()
                headers.append(('Set-Cookie', f'mile_session={session_token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=43200' + ('; Secure' if SECURE else '')))
                return respond(200, {'ok': True})
            if not user:
                raise Problem(401, 'login_required')
            if path == '/api/logout' and method == 'POST':
                c.execute('DELETE FROM sessions WHERE token=?', (digest(token),))
                c.commit()
                headers.append(('Set-Cookie', 'mile_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0' + ('; Secure' if SECURE else '')))
                return respond(200, {'ok': True})
            if path == '/api/players':
                admin(user)
                if method == 'GET':
                    rows = c.execute("SELECT u.id,u.name,u.email,u.active,(u.password IS NOT NULL) activated,(SELECT count(*) FROM documents d WHERE d.user_id=u.id) documents FROM users u WHERE role='player' ORDER BY u.name").fetchall()
                    return respond(200, {'players': [dict(r) for r in rows]})
                if method == 'POST':
                    body = read_json(env)
                    name, email = str(body.get('name','')).strip(), str(body.get('email','')).strip().lower()
                    if not name or len(name) > 120 or len(email) > 254 or '@' not in email or ' ' in email:
                        raise Problem(400, 'user_fields')
                    uid = secrets.token_hex(16)
                    c.execute('INSERT INTO users(id,name,email,role) VALUES(?,?,?,?)', (uid,name,email,'player'))
                    link = activation(c,uid)
                    c.commit()
                    return respond(201, {'activation_url':link})
            if path == '/api/admins' and method == 'GET':
                admin(user)
                rows = c.execute("SELECT id,name,email,active,(password IS NOT NULL) activated FROM users WHERE role='admin' ORDER BY name").fetchall()
                return respond(200, {'admins': [dict(r) for r in rows]})
            if path.startswith('/api/admins/') and method == 'POST':
                admin(user)
                parts = path.split('/')
                if len(parts) != 5:
                    raise Problem(404,'not_found')
                uid, action = parts[3:]
                target = c.execute("SELECT * FROM users WHERE id=? AND role='admin' AND active=1", (uid,)).fetchone()
                if not target:
                    raise Problem(404,'not_found')
                if action == 'activation':
                    link = activation(c,uid)
                    c.commit()
                    return respond(200, {'activation_url':link})
                raise Problem(404,'not_found')
            if path.startswith('/api/players/') and method in ('PUT','DELETE'):
                admin(user)
                parts = path.split('/')
                if len(parts) != 4:
                    raise Problem(404,'not_found')
                uid = parts[3]
                player = c.execute("SELECT * FROM users WHERE id=? AND role='player'",(uid,)).fetchone()
                if not player:
                    raise Problem(404,'not_found')
                if method == 'PUT':
                    body = read_json(env)
                    name, email = str(body.get('name','')).strip(), str(body.get('email','')).strip().lower()
                    if not name or len(name) > 120 or len(email) > 254 or '@' not in email or ' ' in email:
                        raise Problem(400,'user_fields')
                    c.execute('UPDATE users SET name=?,email=? WHERE id=?',(name,email,uid))
                    c.commit()
                    return respond(200,{'ok':True})
                c.execute('DELETE FROM documents WHERE user_id=?',(uid,))
                c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
                c.execute('DELETE FROM activations WHERE user_id=?',(uid,))
                c.execute('DELETE FROM users WHERE id=?',(uid,))
                c.commit()
                return respond(200,{'ok':True})
            if path.startswith('/api/players/') and method == 'POST':
                admin(user)
                parts = path.split('/')
                if len(parts) != 5:
                    raise Problem(404,'not_found')
                uid, action = parts[3:]
                player = c.execute("SELECT * FROM users WHERE id=? AND role='player'",(uid,)).fetchone()
                if not player:
                    raise Problem(404,'not_found')
                if action == 'activation' and player['active']:
                    link = activation(c,uid)
                    c.commit()
                    return respond(200, {'activation_url':link})
                if action == 'status':
                    active = read_json(env).get('active')
                    if not isinstance(active,bool):
                        raise Problem(400,'user_fields')
                    c.execute('UPDATE users SET active=? WHERE id=?',(int(active),uid))
                    c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
                    c.execute('DELETE FROM activations WHERE user_id=?',(uid,))
                    c.commit()
                    return respond(200,{'ok':True})
            if path == '/api/documents':
                qs = parse_qs(env.get('QUERY_STRING',''))
                uid = qs.get('player',[user['id']])[0]
                authorize_owner(user, uid)
                owner = c.execute("SELECT id FROM users WHERE id=? AND role='player'",(uid,)).fetchone()
                if not owner:
                    raise Problem(404,'not_found')
                if method == 'GET':
                    rows = c.execute('SELECT id,folder,title,size,updated FROM documents WHERE user_id=? ORDER BY updated DESC',(uid,)).fetchall()
                    return respond(200,{'documents':[dict(r) for r in rows]})
                if method == 'POST':
                    admin(user)
                    folder = qs.get('folder',[''])[0]
                    title = qs.get('title',[''])[0].strip()
                    if folder not in FOLDERS or not title or len(title)>180 or any(ord(ch)<32 for ch in title):
                        raise Problem(400,'document_fields')
                    blob = read_body(env, MAX_PDF)
                    if not blob.startswith(b'%PDF-') or b'%%EOF' not in blob[-4096:]:
                        raise Problem(400,'pdf_only')
                    if not title or len(title) > 180 or any(ord(ch) < 32 for ch in title):
                        raise Problem(400,'document_fields')
                    did = secrets.token_hex(16)
                    c.execute('INSERT INTO documents(id,user_id,folder,title,size,updated,uploaded_by,data) VALUES(?,?,?,?,?,?,?,?)',(did,uid,folder,title,len(blob),now,user['id'],blob))
                    c.commit()
                    return respond(201,{'id':did})
            if path.startswith('/api/documents/'):
                did = path.split('/')[-1]
                d = c.execute('SELECT * FROM documents WHERE id=?',(did,)).fetchone()
                if not d:
                    raise Problem(404,'not_found')
                authorize_owner(user,d['user_id'])
                if method == 'PATCH':
                    admin(user)
                    payload = read_json(env)
                    title = str(payload.get('title','')).strip()
                    if not title or len(title) > 180 or any(ord(ch) < 32 for ch in title):
                        raise Problem(400,'document_fields')
                    c.execute('UPDATE documents SET title=?,updated=? WHERE id=?',(title,now,d['id']))
                    c.commit()
                    return respond(200,{'ok':True})
                if method == 'PUT':
                    admin(user)
                    blob = read_body(env, MAX_PDF)
                    if not blob.startswith(b'%PDF-') or b'%%EOF' not in blob[-4096:]:
                        raise Problem(400,'pdf_only')
                    c.execute('UPDATE documents SET size=?,updated=?,uploaded_by=?,data=? WHERE id=?',(len(blob),now,user['id'],blob,d['id']))
                    c.commit()
                    return respond(200,{'ok':True})
                if method == 'GET':
                    headers.append(('Content-Disposition', "inline; filename=document.pdf; filename*=UTF-8''" + quote((d['title'] if d['title'].lower().endswith('.pdf') else d['title'] + '.pdf'),safe='')))
                    return respond(200,bytes(d['data']),'application/pdf')
                if method == 'DELETE':
                    admin(user)
                    c.execute('DELETE FROM documents WHERE id=?',(did,))
                    c.commit()
                    return respond(200,{'ok':True})
            raise Problem(404,'not_found')
    except Problem as e:
        return respond(e.status, {'error':e.code})
    except sqlite3.IntegrityError:
        return respond(409, {'error':'email_exists'})
    except (ValueError, json.JSONDecodeError):
        return respond(400, {'error':'invalid_request'})
    except Exception as e:
        if psycopg is not None and isinstance(e, psycopg.errors.UniqueViolation):
            return respond(409, {'error':'email_exists'})
        logging.exception('The Mile request failed')
        return respond(500, {'error':'server_error'})

def read_body(env, limit):
    try:
        length = int(env.get('CONTENT_LENGTH') or 0)
    except ValueError:
        raise Problem(400,'invalid_request')
    if length <= 0:
        raise Problem(400,'invalid_request')
    if length > limit:
        raise Problem(413,'file_size')
    data = env['wsgi.input'].read(length)
    if len(data) != length:
        raise Problem(400,'invalid_request')
    return data

def read_json(env):
    value = json.loads(read_body(env, 8192))
    if not isinstance(value, dict):
        raise Problem(400,'invalid_request')
    return value

def admin(user):
    if user['role'] != 'admin':
        raise Problem(403,'forbidden')

def authorize_owner(user, uid):
    if user['role'] != 'admin' and user['id'] != uid:
        raise Problem(403,'forbidden')

def rate_limit(c, key, now):
    row = c.execute('SELECT * FROM attempts WHERE key=?',(key,)).fetchone()
    if row and row['until_time'] > now and row['count'] >= 10:
        raise Problem(429,'rate_limit')
    count = row['count']+1 if row and row['until_time']>now else 1
    until = row['until_time'] if row and row['until_time']>now else now+900
    c.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)',(key,count,until))
    c.execute('DELETE FROM attempts WHERE until_time<=?',(now,))
    c.commit()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('init','activate','serve'))
    parser.add_argument('--email')
    args=parser.parse_args()
    initialize()
    if args.command=='activate':
        with connect() as c:
            user=c.execute('SELECT id FROM users WHERE email=? AND active=1',((args.email or '').lower(),)).fetchone()
            if not user:
                parser.error('Conta inexistente ou desativada.')
            print(activation(c,user['id']))
    elif args.command=='serve':
        from wsgiref.simple_server import make_server
        print('Desenvolvimento local: http://localhost:8000')
        make_server('127.0.0.1',8000,application).serve_forever()
