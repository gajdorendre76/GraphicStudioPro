#!/usr/bin/env python3
"""Graphic Studio Pro: helyi project- és color palette-központ."""
import json, re, secrets, subprocess, sys, threading, webbrowser, io, zipfile, mimetypes, os, datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote
from tkinter import Tk, Frame, Label, Button, Entry, Listbox, END, messagebox, StringVar

ROOT=Path(__file__).resolve().parent
DATA=Path.home()/'.local/share/grafikai-studio-pro'
DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'projects.json'
LOCK=threading.RLock()
TOKEN=secrets.token_urlsafe(24)
HEX=re.compile(r'^#[0-9a-fA-F]{6}$')
VAULT=DATA/'dokumentumok'
VAULT.mkdir(exist_ok=True)
BACKUPS=DATA/'biztonsagi_mentesek'
BACKUPS.mkdir(exist_ok=True)
MAX_BACKUPS=12
EXTS={'.json','.png','.jpg','.jpeg','.webp','.svg','.pdf','.txt'}
MAX_UPLOAD=20*1024*1024
MAX_FILES=200
def safe_name(name):
    name=Path(str(name)).name
    if not name or len(name)>120 or name in ('.','..') or not re.fullmatch(r'[\w .()\-]+',name,re.UNICODE):
        raise ValueError('Invalid filenév')
    if Path(name).suffix.lower() not in EXTS: raise ValueError('Nem támogatott filetípus')
    return name
def active_dir(d):
    pid=d.get('active')
    if not isinstance(pid,str) or not re.fullmatch(r'[a-f0-9]{16}',pid) or not any(p.get('id')==pid for p in d['projects']):
        raise ValueError('No active project')
    folder=VAULT/pid;folder.mkdir(exist_ok=True)
    return folder
def list_docs(d):
    folder=active_dir(d)
    return [{'name':p.name,'size':p.stat().st_size} for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in EXTS]


def load():
    try:
        d=json.loads(DB.read_text(encoding='utf-8'))
        return d if isinstance(d,dict) and isinstance(d.get('projects'),list) else {'projects':[]}
    except (OSError,ValueError): return {'projects':[]}

def save(d):
    tmp=DB.with_suffix('.tmp')
    tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(DB)

def validate_colors(values):
    if not isinstance(values,list) or len(values)>40: raise ValueError('Legfeljebb 40 color engedélyezett')
    if not all(isinstance(x,str) and HEX.fullmatch(x) for x in values): raise ValueError('Invalid HEX color')
    return [x.upper() for x in values]

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT),**kw)
    def log_message(self,*args): pass
    def do_GET(self):
        path=urlparse(self.path).path
        if path in ('/api/documents','/api/download','/api/project-zip'):
            if parse_qs(urlparse(self.path).query).get('token',[''])[0]!=TOKEN:
                self.reply({'error':'Hozzáférés megtagadva'},403);return
            try:
                with LOCK:
                    d=load();folder=active_dir(d)
                    if path=='/api/documents': self.reply({'files':list_docs(d)});return
                    if path=='/api/download':
                        name=safe_name(parse_qs(urlparse(self.path).query).get('name',[''])[0]);f=folder/name
                        if not f.is_file():self.reply({'error':'No ilyen file'},404);return
                        self.binary(f.read_bytes(),mimetypes.guess_type(name)[0] or 'application/octet-stream',name);return
                    buf=io.BytesIO()
                    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
                        z.writestr('project.json',json.dumps({'project':next(p for p in d['projects'] if p['id']==d['active'])},ensure_ascii=False,indent=2))
                        for f in folder.iterdir():
                            if f.is_file() and f.suffix.lower() in EXTS: z.write(f,'dokumentumok/'+f.name)
                    self.binary(buf.getvalue(),'application/zip','grafikai-project.zip');return
            except ValueError as e:self.reply({'error':str(e)},400);return
        if path=='/api/backups':
            if parse_qs(urlparse(self.path).query).get('token',[''])[0]!=TOKEN:
                self.reply({'error':'Hozzáférés megtagadva'},403);return
            try:
                with LOCK:
                    d=load();pid=active_dir(d).name;folder=BACKUPS/pid
                    items=[{'name':f.name,'size':f.stat().st_size} for f in sorted(folder.glob('*.json'),reverse=True)] if folder.exists() else []
                self.reply({'backups':items});return
            except ValueError as e:self.reply({'error':str(e)},400);return
        if path=='/api/projects':
            with LOCK: self.reply(load()); return
        if path=='/api/active':
            with LOCK:
                d=load(); self.reply(next((p for p in d['projects'] if p['id']==d.get('active')),{})); return
        if path=='/': self.path='/hub.html'
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path
        if self.headers.get('X-Studio-Token')!=TOKEN: self.reply({'error':'Hozzáférés megtagadva'},403);return
        try:
            if path=='/api/launch-imagebatch':
                with LOCK:
                    d=load();folder=active_dir(d)
                    project=next(p for p in d['projects'] if p['id']==d['active'])
                env=os.environ.copy()
                env['GRAFIKAI_STUDIO_PROJECT_DIR']=str(folder)
                env['GRAFIKAI_STUDIO_PROJECT_NAME']=project['name']
                subprocess.Popen([sys.executable,str(ROOT/'imagebatch_pro_1_0/imagebatch.py')],cwd=str(ROOT/'imagebatch_pro_1_0'),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.reply({'ok':True,'project':project['name']});return
            if path=='/api/upload':
                name=safe_name(self.headers.get('X-File-Name',''))
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>MAX_UPLOAD:raise ValueError('A file 1 bájt és 20 MB közötti lehet')
                raw=self.rfile.read(n)
                if len(raw)!=n:raise ValueError('Hiányos feltöltés')
                if name.lower().endswith('.json'):
                    json.loads(raw.decode('utf-8'))
                with LOCK:
                    folder=active_dir(load())
                    if len(list(folder.iterdir()))>=MAX_FILES and not (folder/name).exists():raise ValueError('A project legfeljebb 200 filet tartalmazhat')
                    tmp=folder/(name+'.tmp');tmp.write_bytes(raw);tmp.replace(folder/name)
                self.reply({'ok':True,'name':name});return
            if path=='/api/autosave':
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>MAX_UPLOAD:raise ValueError('A save legfeljebb 20 MB lehet')
                body=json.loads(self.rfile.read(n))
                if not isinstance(body,dict) or not all(k in body for k in ('identity','layout')):raise ValueError('Hiányos munkamenet')
                with LOCK:
                    d=load();pid=active_dir(d).name
                    if body.get('projectId')!=pid:raise ValueError('Projectváltás történt, save megszakítva')
                    folder=BACKUPS/pid;folder.mkdir(exist_ok=True)
                    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                    target=folder/(stamp+'.json');tmp=folder/(stamp+'.tmp')
                    tmp.write_text(json.dumps({'projectId':pid,'savedAt':datetime.datetime.now().isoformat(timespec='seconds'),'identity':body['identity'],'layout':body['layout']},ensure_ascii=False),encoding='utf-8')
                    tmp.replace(target)
                    for old in sorted(folder.glob('*.json'),reverse=True)[MAX_BACKUPS:]:old.unlink()
                self.reply({'ok':True,'name':target.name});return
            if path=='/api/restore-backup':
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>10000:raise ValueError('Invalid kérés')
                body=json.loads(self.rfile.read(n));name=body.get('name','')
                if not isinstance(name,str) or not re.fullmatch(r'\d{8}-\d{6}-\d{6}\.json',name):raise ValueError('Invalid savenév')
                with LOCK:
                    pid=active_dir(load()).name;f=BACKUPS/pid/name
                    if not f.is_file():raise ValueError('A save nem található')
                    doc=json.loads(f.read_text(encoding='utf-8'))
                    if doc.get('projectId')!=pid:raise ValueError('Eltérő project')
                self.reply({'backup':doc});return
            if path=='/api/remove-document':
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>10000:raise ValueError('Invalid kérés')
                name=safe_name(json.loads(self.rfile.read(n)).get('name',''))
                with LOCK:
                    f=active_dir(load())/name
                    if not f.is_file():raise ValueError('A file nem található')
                    f.unlink()
                self.reply({'ok':True});return
            n=int(self.headers.get('Content-Length','0'))
            if n<1 or n>10000: raise ValueError('Túl nagy vagy üres adat')
            body=json.loads(self.rfile.read(n))
            with LOCK:
                d=load()
                if path=='/api/create':
                    name=body.get('name','').strip()
                    if not 1<=len(name)<=80: raise ValueError('A név 1–80 karakter lehet')
                    p={'id':secrets.token_hex(8),'name':name,'colors':['#202936','#F4F0E8','#D67D36'],'last_opened':datetime.datetime.now(datetime.timezone.utc).isoformat()}
                    d['projects'].append(p);d['active']=p['id']
                elif path=='/api/select':
                    if not any(p['id']==body.get('id') for p in d['projects']): raise ValueError('No ilyen project')
                    d['active']=body['id'];next(p for p in d['projects'] if p['id']==body['id'])['last_opened']=datetime.datetime.now(datetime.timezone.utc).isoformat()
                elif path=='/api/palette':
                    p=next((p for p in d['projects'] if p['id']==d.get('active')),None)
                    if p is None: raise ValueError('Előbb hozz létre projectet')
                    p['colors']=validate_colors(body.get('colors'))
                elif path=='/api/delete':
                    d['projects']=[p for p in d['projects'] if p['id']!=body.get('id')]
                    if d.get('active')==body.get('id'): d['active']=d['projects'][0]['id'] if d['projects'] else None
                else: self.reply({'error':'Ismeretlen művelet'},404);return
                save(d)
            self.reply({'ok':True})
        except (ValueError,TypeError,json.JSONDecodeError) as e: self.reply({'error':str(e)},400)
    def binary(self,data,mime,name):
        self.send_response(200)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(name))
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)
    def reply(self,obj,status=200):
        data=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)

def run():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    port=server.server_address[1]
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{port}/?token={TOKEN}'
    root=Tk();root.title('Graphic Studio Pro 10.0');root.geometry('640x480');root.minsize(500,400)
    main=Frame(root,padx=22,pady=18);main.pack(fill='both',expand=True)
    Label(main,text='GRAPHIC STUDIO PRO',font=('DejaVu Sans',19,'bold')).pack(anchor='w')
    Label(main,text='Közös munkaterület • projectpaletták • 3 grafikai eszköz').pack(anchor='w',pady=(3,18))
    Button(main,text='Közös munkaterület open',command=lambda:webbrowser.open(url),height=2).pack(fill='x')
    Label(main,text='Projects',font=('DejaVu Sans',12,'bold')).pack(anchor='w',pady=(20,4))
    names=Listbox(main,height=6);names.pack(fill='both',expand=True)
    status=StringVar(value='A projectadatok helyben tárolódnak.')
    def refresh():
        names.delete(0,END)
        with LOCK: d=load()
        for p in d['projects']: names.insert(END,('● ' if p['id']==d.get('active') else '   ')+p['name'])
        return d
    def create():
        name=entry.get().strip()
        if not name: messagebox.showwarning('Project','Adj meg egy nevet');return
        with LOCK:
            d=load();p={'id':secrets.token_hex(8),'name':name,'colors':['#202936','#F4F0E8','#D67D36'],'last_opened':datetime.datetime.now(datetime.timezone.utc).isoformat()};d['projects'].append(p);d['active']=p['id'];save(d)
        entry.delete(0,END);refresh();status.set('Project created.')
    def select():
        sel=names.curselection()
        if not sel:return
        with LOCK:
            d=load();d['active']=d['projects'][sel[0]]['id'];d['projects'][sel[0]]['last_opened']=datetime.datetime.now(datetime.timezone.utc).isoformat();save(d)
        refresh();status.set('Active project kiválasztva. Frissítsd a webes munkaterületet.')
    line=Frame(main);line.pack(fill='x',pady=7)
    entry=Entry(line);entry.pack(side='left',fill='x',expand=True)
    Button(line,text='New project',command=create).pack(side='left',padx=5)
    Button(main,text='Selected project aktiválása',command=select).pack(anchor='w')
    def launch_batch():
        with LOCK:
            d=load()
            try:
                folder=active_dir(d)
                project=next(p for p in d['projects'] if p['id']==d['active'])
            except (ValueError, KeyError, StopIteration):
                messagebox.showwarning('No active project','Előbb hozz létre vagy choose ki egy projectet.');return
        env=os.environ.copy()
        env['GRAFIKAI_STUDIO_PROJECT_DIR']=str(folder)
        env['GRAFIKAI_STUDIO_PROJECT_NAME']=project['name']
        subprocess.Popen([sys.executable,str(ROOT/'imagebatch_pro_1_0/imagebatch.py')],cwd=str(ROOT/'imagebatch_pro_1_0'),env=env)
        status.set('ImageBatch elindítva: '+project['name']+' – a kimeneti mappa a projectfiletár.')
    Button(main,text='ImageBatch Pro – save az aktív projectbe',command=launch_batch).pack(anchor='w',pady=(12,0))
    Label(main,textvariable=status,wraplength=550).pack(anchor='w',pady=10)
    refresh();root.protocol('WM_DELETE_WINDOW',lambda:(server.shutdown(),root.destroy()));root.mainloop()

if __name__=='__main__':run()
