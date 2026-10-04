import csv, io, json, os, re, sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('APPOINTMENT_DB', BASE_DIR / 'instance' / 'appointments.db'))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
PORT = int(os.environ.get('PORT', '5000'))
ALLOWED_STATUS = {'Scheduled', 'Completed', 'Cancelled'}

MIME = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'application/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.csv':'text/csv; charset=utf-8'}

def db():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row; return c

def init_db():
    with db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL,
            date TEXT NOT NULL, time TEXT NOT NULL, purpose TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        c.commit()

def normalize_date(v):
    v = str(v or '').strip()
    if not v: raise ValueError('Date is required.')
    v = re.sub(r'[/.]', '-', v)
    try: return datetime.strptime(v, '%d-%m-%Y').strftime('%d-%m-%Y')
    except ValueError: raise ValueError('Date must be in DD-MM-YYYY format, for example 15-10-2026.')

def normalize_time(v):
    v = str(v or '').strip()
    try: return datetime.strptime(v, '%H:%M').strftime('%H:%M')
    except ValueError: raise ValueError('Time must be in 24-hour HH:MM format, for example 10:30.')

def validate(data):
    name, phone, purpose = str(data.get('name','')).strip(), str(data.get('phone','')).strip(), str(data.get('purpose','')).strip()
    status = str(data.get('status','Scheduled')).strip() or 'Scheduled'
    if not all((name, phone, purpose)): raise ValueError('Please fill all appointment fields.')
    if not phone.isdigit() or not 10 <= len(phone) <= 15: raise ValueError('Enter a valid phone number (10-15 digits).')
    if status not in ALLOWED_STATUS: raise ValueError('Invalid appointment status.')
    return name, phone, normalize_date(data.get('date')), normalize_time(data.get('time')), purpose, status

def row(r): return {k:r[k] for k in ('id','name','phone','date','time','purpose','status')}

def send_json(h, data, code=200):
    raw=json.dumps(data).encode(); h.send_response(code); h.send_header('Content-Type','application/json; charset=utf-8'); h.send_header('Content-Length',str(len(raw))); h.end_headers(); h.wfile.write(raw)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print('%s - %s' % (self.address_string(), fmt % args))
    def read_json(self):
        n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or b'{}')
    def do_GET(self):
        p=urlparse(self.path)
        if p.path in ('/','/index.html'):
            raw=(BASE_DIR/'templates'/'index.html').read_bytes(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if p.path=='/health': send_json(self,{'status':'ok'}); return
        if p.path=='/api/appointments':
            q=parse_qs(p.query).get('q',[''])[0].strip(); like=f'%{q}%'
            with db() as c:
                rows=c.execute('SELECT * FROM appointments WHERE ?="" OR name LIKE ? OR phone LIKE ? OR purpose LIKE ? OR status LIKE ? OR date LIKE ? ORDER BY date,time,id DESC',(q,like,like,like,like,like)).fetchall()
            send_json(self,[row(r) for r in rows]); return
        if p.path=='/api/stats':
            with db() as c:
                out={s:c.execute('SELECT COUNT(*) FROM appointments'+(' WHERE status=?' if s!='total' else ''),(() if s=='total' else (s.capitalize(),))).fetchone()[0] for s in ['total','scheduled','completed','cancelled']}
            send_json(self,out); return
        if p.path=='/api/export':
            with db() as c: rows=c.execute('SELECT id,name,phone,date,time,purpose,status FROM appointments ORDER BY date,time,id').fetchall()
            s=io.StringIO(); w=csv.writer(s); w.writerow(['ID','Name','Phone','Date','Time','Purpose','Status']); [w.writerow([r[k] for k in ('id','name','phone','date','time','purpose','status')]) for r in rows]
            raw=s.getvalue().encode(); self.send_response(200); self.send_header('Content-Type','text/csv; charset=utf-8'); self.send_header('Content-Disposition','attachment; filename="appointment_records.csv"'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if p.path.startswith('/static/'):
            rel=p.path.removeprefix('/static/'); fp=(BASE_DIR/'static'/rel).resolve()
            if BASE_DIR/'static' not in fp.parents: self.send_error(404); return
            if fp.is_file():
                raw=fp.read_bytes(); self.send_response(200); self.send_header('Content-Type',MIME.get(fp.suffix,'application/octet-stream')); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        self.send_error(404)
    def do_POST(self): self.mutate('POST')
    def do_PUT(self): self.mutate('PUT')
    def do_DELETE(self): self.mutate('DELETE')
    def mutate(self, method):
        p=urlparse(self.path); parts=p.path.strip('/').split('/')
        try:
            if method=='POST' and p.path=='/api/appointments':
                vals=validate(self.read_json())
                with db() as c:
                    cur=c.execute('INSERT INTO appointments(name,phone,date,time,purpose,status) VALUES(?,?,?,?,?,?)',vals); r=c.execute('SELECT * FROM appointments WHERE id=?',(cur.lastrowid,)).fetchone(); c.commit()
                send_json(self,row(r),201); return
            if len(parts)==3 and parts[:2]==['api','appointments'] and parts[2].isdigit():
                aid=int(parts[2])
                if method=='DELETE':
                    with db() as c: cur=c.execute('DELETE FROM appointments WHERE id=?',(aid,)); c.commit()
                    if not cur.rowcount: send_json(self,{'error':'Appointment not found.'},404)
                    else: send_json(self,{'message':'Appointment deleted successfully.'})
                    return
                if method=='PUT':
                    vals=validate(self.read_json())
                    with db() as c:
                        if not c.execute('SELECT id FROM appointments WHERE id=?',(aid,)).fetchone(): send_json(self,{'error':'Appointment not found.'},404); return
                        c.execute('UPDATE appointments SET name=?,phone=?,date=?,time=?,purpose=?,status=? WHERE id=?',(*vals,aid)); r=c.execute('SELECT * FROM appointments WHERE id=?',(aid,)).fetchone(); c.commit()
                    send_json(self,row(r)); return
            self.send_error(404)
        except ValueError as e: send_json(self,{'error':str(e)},400)
        except (sqlite3.Error,json.JSONDecodeError) as e: send_json(self,{'error':'Invalid request or database error.'},400)

init_db()
if __name__=='__main__':
    print(f'Appointment Management System running on http://0.0.0.0:{PORT}')
    ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
