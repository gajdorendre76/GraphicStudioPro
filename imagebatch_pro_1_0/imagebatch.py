#!/usr/bin/env python3
"""ImageBatch - magyar nyelvű kötegelt imagefeldolgozó."""
import os
import json
import threading
import queue
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageEnhance, ImageTk, UnidentifiedImageError

FORMATS = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}
PRESETS = {'Egyedi': None, 'Instagram négyzet (1080×1080)': (1080,1080), 'Instagram álló (1080×1350)': (1080,1350), 'Facebook poszt (1200×630)': (1200,630), 'YouTube bélyegimage (1280×720)': (1280,720), 'Webpage (1600×900)': (1600,900)}
EXTS = {'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff','.gif'}

class App:
    def __init__(self, root):
        self.root = root
        root.title('ImageBatch Pro – Grafikai Stúdió 5.0')
        root.geometry('1100x850')
        root.minsize(760,580)
        self.files = []
        self.events = queue.Queue()
        self.running = False
        self.project_dir = None
        requested = os.environ.get('GRAFIKAI_STUDIO_PROJECT_DIR','')
        if requested:
            folder=Path(requested).expanduser().resolve()
            vault=(Path.home()/'.local/share/grafikai-studio-pro/dokumentumok').resolve()
            if folder.parent == vault and len(folder.name)==16 and all(c in '0123456789abcdef' for c in folder.name) and folder.is_dir():
                self.project_dir=folder
        self.outdir = tk.StringVar(value=str(self.project_dir or (Path.home()/'Images'/'ImageBatch')))
        self.fmt = tk.StringVar(value='JPEG')
        self.mode = tk.StringVar(value='Aránytartó illesztés')
        self.preset = tk.StringVar(value='Egyedi')
        self.width = tk.StringVar(value='1200')
        self.height = tk.StringVar(value='1200')
        self.quality = tk.IntVar(value=88)
        self.watermark = tk.StringVar()
        self.opacity = tk.IntVar(value=65)
        self.suffix = tk.StringVar(value='_kesz')
        self.prefix = tk.StringVar(value='')
        self.numbering = tk.BooleanVar(value=False)
        self.number_start = tk.StringVar(value='1')
        self.number_digits = tk.StringVar(value='3')
        self.rotation = tk.StringVar(value='0°')
        self.brightness = tk.DoubleVar(value=1.0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.logo_path = tk.StringVar()
        self.logo_scale = tk.IntVar(value=20)
        self.keep_exif = tk.BooleanVar(value=False)
        self.keep_icc = tk.BooleanVar(value=True)
        self.dpi = tk.StringVar(value='300')
        self.watermark_position = tk.StringVar(value='Jobb alsó')
        self.optimize = tk.BooleanVar(value=True)
        self.cancel_requested = threading.Event()
        self.preview_image = None
        self.preview_job = None
        self.progress = tk.DoubleVar(value=0)
        self.status = tk.StringVar(value='Choose imageset a kezdéshez.')
        self.make_ui()
        root.after(100,self.poll)
        for var in (self.width,self.height,self.mode,self.rotation,self.brightness,self.contrast,self.watermark,self.opacity,self.logo_path,self.logo_scale,self.watermark_position):
            var.trace_add('write',lambda *_:self.schedule_preview())

    def make_ui(self):
        main = ttk.Frame(self.root,padding=14)
        main.pack(fill='both',expand=True)
        ttk.Label(main,text='ImageBatch Pro',font=('Sans',22,'bold')).pack(anchor='w')
        ttk.Label(main,text='Images átméretezése, konvertálása és vízjelezése – egyszerre, biztonságosan.').pack(anchor='w',pady=(0,10))
        if self.project_dir:
            project_name=os.environ.get('GRAFIKAI_STUDIO_PROJECT_NAME','Active project')
            ttk.Label(main,text='Project: '+project_name+' | Kimenet: közös projectfiletár',foreground='#176b48').pack(anchor='w',pady=(0,8))
            ttk.Button(main,text='Vissza a project kimeneti mappájához',command=lambda:self.outdir.set(str(self.project_dir))).pack(anchor='w',pady=(0,8))
        buttons = ttk.Frame(main)
        buttons.pack(fill='x')
        ttk.Button(buttons,text='Images add',command=self.add_files).pack(side='left',padx=(0,6))
        ttk.Button(buttons,text='Folder add',command=self.add_folder).pack(side='left',padx=(0,6))
        ttk.Button(buttons,text='Lista ürítése',command=self.clear).pack(side='left')
        self.file_list = tk.Listbox(main,height=8,selectmode='extended')
        self.file_list.pack(fill='both',expand=True,pady=(8,5))
        self.file_list.bind('<<ListboxSelect>>',self.preview_selected)
        prev=ttk.Frame(main);prev.pack(fill='x',pady=(0,8))
        self.preview_label=ttk.Label(prev,text='Élő preview: jelölj ki egy imageet.',anchor='center')
        self.preview_label.pack(fill='x')
        options = ttk.LabelFrame(main,text='Processingi settings',padding=10)
        options.pack(fill='x')
        def line():
            f=ttk.Frame(options); f.pack(fill='x',pady=3); return f
        f=line()
        ttk.Label(f,text='Size sablon:',width=18).pack(side='left')
        preset=ttk.Combobox(f,textvariable=self.preset,values=list(PRESETS),state='readonly',width=37)
        preset.pack(side='left'); preset.bind('<<ComboboxSelected>>',self.set_preset)
        f=line()
        ttk.Label(f,text='Width (px):',width=18).pack(side='left')
        ttk.Entry(f,textvariable=self.width,width=10).pack(side='left')
        ttk.Label(f,text='Height (px):').pack(side='left',padx=(15,5))
        ttk.Entry(f,textvariable=self.height,width=10).pack(side='left')
        f=line()
        ttk.Label(f,text='Sizeezési mód:',width=18).pack(side='left')
        ttk.Combobox(f,textvariable=self.mode,values=['Aránytartó illesztés','Kitöltés / középre vágás','Pontos méret / torzítás'],state='readonly',width=37).pack(side='left')
        f=line()
        ttk.Label(f,text='Output formátum:',width=18).pack(side='left')
        ttk.Combobox(f,textvariable=self.fmt,values=list(FORMATS),state='readonly',width=12).pack(side='left')
        ttk.Label(f,text='Minőség (JPEG/WebP):').pack(side='left',padx=(15,5))
        ttk.Spinbox(f,from_=1,to=100,textvariable=self.quality,width=5).pack(side='left')
        f=line()
        ttk.Label(f,text='Watermark text:',width=18).pack(side='left')
        ttk.Entry(f,textvariable=self.watermark,width=35).pack(side='left')
        ttk.Label(f,text='Fedettség (%):').pack(side='left',padx=(15,5))
        ttk.Spinbox(f,from_=0,to=100,textvariable=self.opacity,width=5).pack(side='left')
        f=line()
        ttk.Label(f,text='Forgatás:',width=18).pack(side='left')
        ttk.Combobox(f,textvariable=self.rotation,values=['0°','90° jobbra','180°','90° balra'],state='readonly',width=20).pack(side='left')
        f=line()
        ttk.Label(f,text='Fényerő:',width=18).pack(side='left')
        ttk.Scale(f,from_=0.2,to=2.0,variable=self.brightness,orient='horizontal',length=170).pack(side='left')
        ttk.Label(f,text='Kontraszt:').pack(side='left',padx=(15,5))
        ttk.Scale(f,from_=0.2,to=2.0,variable=self.contrast,orient='horizontal',length=170).pack(side='left')
        f=line()
        ttk.Label(f,text='Logo vízjel:',width=18).pack(side='left')
        ttk.Entry(f,textvariable=self.logo_path,width=42).pack(side='left',fill='x',expand=True)
        ttk.Button(f,text='Select',command=self.choose_logo).pack(side='left',padx=(5,0))
        f=line()
        ttk.Label(f,text='Logo szélesség (%):',width=18).pack(side='left')
        ttk.Spinbox(f,from_=1,to=80,textvariable=self.logo_scale,width=5).pack(side='left')
        ttk.Checkbutton(f,text='EXIF megtartása (JPEG/WebP)',variable=self.keep_exif).pack(side='left',padx=(16,0))
        ttk.Checkbutton(f,text='ICC colorprofil megtartása',variable=self.keep_icc).pack(side='left',padx=(12,0))
        f=line()
        ttk.Label(f,text='Watermark helye:',width=18).pack(side='left')
        ttk.Combobox(f,textvariable=self.watermark_position,values=['Bal felső','Felső közép','Jobb felső','Bal közép','Középen','Jobb közép','Bal alsó','Alsó közép','Jobb alsó'],state='readonly',width=20).pack(side='left')
        ttk.Label(f,text='DPI:').pack(side='left',padx=(14,5))
        ttk.Entry(f,textvariable=self.dpi,width=7).pack(side='left')
        ttk.Checkbutton(f,text='Optimalizálás',variable=self.optimize).pack(side='left',padx=(15,0))
        f=line()
        ttk.Label(f,text='Filenév előtag:',width=18).pack(side='left')
        ttk.Entry(f,textvariable=self.prefix,width=14).pack(side='left')
        ttk.Label(f,text='Utótag:').pack(side='left',padx=(12,4))
        ttk.Entry(f,textvariable=self.suffix,width=14).pack(side='left')
        f=line()
        ttk.Checkbutton(f,text='Sorszámozott átnevezés',variable=self.numbering).pack(side='left')
        ttk.Label(f,text='Kezdőszám:').pack(side='left',padx=(12,4))
        ttk.Entry(f,textvariable=self.number_start,width=7).pack(side='left')
        ttk.Label(f,text='Számjegyek:').pack(side='left',padx=(12,4))
        ttk.Entry(f,textvariable=self.number_digits,width=5).pack(side='left')
        f=line()
        ttk.Button(f,text='Profil savee',command=self.save_profile).pack(side='left',padx=(0,8))
        ttk.Button(f,text='Profil betöltése',command=self.load_profile).pack(side='left')
        f=line()
        ttk.Label(f,text='Output mappa:',width=18).pack(side='left')
        ttk.Entry(f,textvariable=self.outdir).pack(side='left',fill='x',expand=True)
        ttk.Button(f,text='Browse',command=self.choose_out).pack(side='left',padx=(6,0))
        ttk.Label(main,text='Az eredeti filesat nem módosítja. Azonos nevű kimenet esetén új sorszámot ad.').pack(anchor='w',pady=(10,4))
        self.startbtn=ttk.Button(main,text='Processing launch',command=self.start)
        self.startbtn.pack(fill='x',pady=(0,5))
        self.cancelbtn=ttk.Button(main,text='Processing megszakítása',command=self.cancel,state='disabled')
        self.cancelbtn.pack(fill='x',pady=(0,8))
        ttk.Progressbar(main,variable=self.progress,maximum=100).pack(fill='x')
        ttk.Label(main,textvariable=self.status).pack(anchor='w',pady=(5,0))

    def choose_logo(self):
        path=filedialog.askopenfilename(title='Watermark logo kiválasztása',filetypes=[('Images','*.png *.webp *.jpg *.jpeg'),('Minden file','*.*')])
        if path:self.logo_path.set(path)

    def schedule_preview(self):
        if self.preview_job is not None:
            self.root.after_cancel(self.preview_job)
        self.preview_job=self.root.after(250,self.preview_selected)

    @staticmethod
    def transform(im,w,h,mode,rotation,brightness,contrast,mark,opacity,logo,logo_scale,position="Jobb alsó"):
        if rotation=='90° jobbra':im=im.transpose(Image.Transpose.ROTATE_270)
        elif rotation=='180°':im=im.transpose(Image.Transpose.ROTATE_180)
        elif rotation=='90° balra':im=im.transpose(Image.Transpose.ROTATE_90)
        if mode=='Kitöltés / középre vágás':
            im=ImageOps.fit(im,(w,h),method=Image.Resampling.LANCZOS)
        elif mode=='Pontos méret / torzítás':
            im=im.resize((w,h),Image.Resampling.LANCZOS)
        else:
            im.thumbnail((w,h),Image.Resampling.LANCZOS)
        im=ImageEnhance.Brightness(im).enhance(brightness)
        im=ImageEnhance.Contrast(im).enhance(contrast)
        im=App.add_mark(im,mark,opacity,position)
        return App.add_logo(im,logo,logo_scale,opacity,position)

    def preview_selected(self,_=None):
        self.preview_job=None
        sel=self.file_list.curselection()
        if not sel:return
        try:
            w,h=int(self.width.get()),int(self.height.get())
            if not (1<=w<=20000 and 1<=h<=20000):raise ValueError('Invalid méret')
            # Korlátozott previewi feldolgozás: nem készítünk több tízezer pixeles imageet.
            with Image.open(self.files[sel[0]]) as src:
                im=ImageOps.exif_transpose(src).copy()
            im.thumbnail((900,900),Image.Resampling.LANCZOS)
            scale=min(1,900/max(w,h))
            pw,ph=max(1,round(w*scale)),max(1,round(h*scale))
            im=self.transform(im,pw,ph,self.mode.get(),self.rotation.get(),float(self.brightness.get()),float(self.contrast.get()),self.watermark.get(),int(self.opacity.get()),self.logo_path.get().strip(),int(self.logo_scale.get()),self.watermark_position.get())
            im.thumbnail((600,190),Image.Resampling.LANCZOS)
            self.preview_image=ImageTk.PhotoImage(im.convert('RGBA'))
            self.preview_label.configure(image=self.preview_image,text='')
        except (OSError,ValueError,tk.TclError) as exc:
            self.preview_label.configure(image='',text=f'Preview nem elérhető: {exc}')

    def profile_data(self):
        keys=('fmt','mode','preset','width','height','quality','watermark','opacity','suffix','prefix','numbering','number_start','number_digits','rotation','brightness','contrast','logo_path','logo_scale','keep_exif','keep_icc','dpi','watermark_position','optimize')
        return {'version':4,'settings':{k:getattr(self,k).get() for k in keys}}

    def save_profile(self):
        path=filedialog.asksaveasfilename(title='Processingi profil savee',defaultextension='.json',filetypes=[('JSON profil','*.json')])
        if path:
            try:Path(path).write_text(json.dumps(self.profile_data(),ensure_ascii=False,indent=2),encoding='utf-8')
            except OSError as exc:messagebox.showerror('Savei error',str(exc))

    def load_profile(self):
        if self.running:return
        path=filedialog.askopenfilename(title='Profil betöltése',filetypes=[('JSON profil','*.json')])
        if not path:return
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8'))
            if not isinstance(data,dict) or not isinstance(data.get('settings'),dict):raise ValueError('Nem ImageBatch profil.')
            for key,value in data['settings'].items():
                if key in self.profile_data()['settings']:
                    getattr(self,key).set(value)
            self.schedule_preview()
        except (OSError,ValueError,TypeError,tk.TclError) as exc:messagebox.showerror('Betöltési error',str(exc))

    def add_files(self):
        paths=filedialog.askopenfilenames(title='Images kiválasztása',filetypes=[('Imagefiles','*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif'),('Minden file','*.*')])
        self.add_paths(paths)
    def add_folder(self):
        folder=filedialog.askdirectory(title='Imagemappa kiválasztása')
        if folder:
            self.add_paths(sorted(str(p) for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in EXTS))
    def add_paths(self,paths):
        known=set(self.files)
        for p in paths:
            if p not in known and Path(p).suffix.lower() in EXTS:
                self.files.append(p); self.file_list.insert('end',p); known.add(p)
        self.status.set(f'{len(self.files)} image a listában.')
    def clear(self):
        if not self.running:
            self.files.clear(); self.file_list.delete(0,'end'); self.preview_label.configure(image='',text='Preview: jelölj ki egy imageet.'); self.preview_image=None; self.status.set('Lista ürítve.')
    def choose_out(self):
        d=filedialog.askdirectory(title='Output mappa')
        if d: self.outdir.set(d)
    def set_preset(self,_=None):
        size=PRESETS[self.preset.get()]
        if size: self.width.set(str(size[0])); self.height.set(str(size[1]))
    def start(self):
        if self.running:return
        if not self.files:
            messagebox.showwarning('Noenek images','Először adj hozzá imageset.');return
        try:
            w,h=int(self.width.get()),int(self.height.get())
            q=int(self.quality.get()); op=int(self.opacity.get())
            if not (1<=w<=20000 and 1<=h<=20000 and 1<=q<=100 and 0<=op<=100 and 1<=self.logo_scale.get()<=80):raise ValueError
            nstart=int(self.number_start.get());ndigits=int(self.number_digits.get())
            if not (0<=nstart<=999999999 and 1<=ndigits<=12):raise ValueError
            dpi=int(self.dpi.get())
            if not 1<=dpi<=2400:raise ValueError('A DPI 1–2400 között lehet.')
            out=Path(self.outdir.get()).expanduser().resolve()
            if not self.outdir.get().strip():raise ValueError
            out.mkdir(parents=True,exist_ok=True)
        except (ValueError,OSError) as exc:
            messagebox.showerror('Hibás beállítás','Ellenőrizd a méretet, minőséget, fedettséget és kimeneti mappát.\n'+str(exc));return
        logo=self.logo_path.get().strip()
        if logo and not Path(logo).is_file():
            messagebox.showerror('Hibás logo','A megadott logofile nem található.');return
        settings=(list(self.files),out,w,h,self.mode.get(),self.fmt.get(),q,self.watermark.get(),op,self.suffix.get(),self.rotation.get(),self.brightness.get(),self.contrast.get(),logo,self.logo_scale.get(),self.keep_exif.get(),self.keep_icc.get(),self.prefix.get(),self.numbering.get(),nstart,ndigits,dpi,self.watermark_position.get(),self.optimize.get())
        self.cancel_requested.clear();self.running=True;self.startbtn.configure(state='disabled');self.cancelbtn.configure(state='normal');self.progress.set(0)
        threading.Thread(target=self.worker,args=(settings,),daemon=True).start()
    def cancel(self):
        if self.running:
            self.cancel_requested.set()
            self.status.set('Megszakítás kérve – az aktuális image még befejeződik.')

    @staticmethod
    def position_xy(position,canvas_w,canvas_h,obj_w,obj_h,margin):
        cols={'Bal':margin,'közép':max(0,(canvas_w-obj_w)//2),'Jobb':max(0,canvas_w-obj_w-margin)}
        rows={'felső':margin,'közép':max(0,(canvas_h-obj_h)//2),'alsó':max(0,canvas_h-obj_h-margin)}
        parts=position.split()
        if position=='Középen':return cols['közép'],rows['közép']
        if len(parts)!=2:return cols['Jobb'],rows['alsó']
        horizontal=parts[0] if parts[0] in ('Bal','Jobb') else 'közép'
        vertical=parts[1] if parts[1] in ('felső','alsó') else 'közép'
        if parts[0]=='Felső':horizontal='közép';vertical='felső'
        if parts[0]=='Alsó':horizontal='közép';vertical='alsó'
        return cols[horizontal],rows[vertical]

    @staticmethod
    def unique_path(out,stem,ext):
        candidate=out/(stem+ext);i=2
        while candidate.exists():
            candidate=out/(f'{stem}_{i}'+ext);i+=1
        return candidate
    @staticmethod
    def add_mark(img,mark,opacity,position="Jobb alsó"):
        if not mark.strip() or opacity==0:return img
        img=img.convert('RGBA')
        layer=Image.new('RGBA',img.size,(0,0,0,0))
        draw=ImageDraw.Draw(layer)
        size=max(14,min(img.width,img.height)//24)
        try:font=ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf',size)
        except OSError:font=ImageFont.load_default()
        bbox=draw.textbbox((0,0),mark,font=font)
        tw,th=bbox[2]-bbox[0],bbox[3]-bbox[1]
        x,y=App.position_xy(position,img.width,img.height,tw,th,max(5,min(img.size)//40))
        draw.text((x,y),mark,font=font,fill=(255,255,255,round(opacity*255/100)),stroke_width=max(1,size//18),stroke_fill=(0,0,0,round(opacity*180/100)))
        return Image.alpha_composite(img,layer)
    @staticmethod
    def add_logo(im,logo_path,scale,opacity,position="Jobb alsó"):
        if not logo_path or opacity==0:return im
        with Image.open(logo_path) as source:
            logo=ImageOps.exif_transpose(source).convert('RGBA')
        width=max(1,round(im.width*scale/100))
        height=max(1,round(logo.height*width/logo.width))
        if height>im.height*0.8:
            height=max(1,round(im.height*0.8));width=max(1,round(logo.width*height/logo.height))
        logo=logo.resize((width,height),Image.Resampling.LANCZOS)
        logo.putalpha(logo.getchannel('A').point(lambda v:round(v*opacity/100)))
        base=im.convert('RGBA')
        margin=max(8,min(im.size)//40)
        base.alpha_composite(logo,App.position_xy(position,im.width,im.height,width,height,margin))
        return base

    def worker(self,settings):
        paths,out,w,h,mode,fmt,quality,mark,opacity,suffix,rotation,brightness,contrast,logo,logo_scale,keep_exif,keep_icc,prefix,numbering,nstart,ndigits,dpi,position,optimize=settings
        good=0;bad=[];log=[];cancelled=False
        started=datetime.now().isoformat(timespec='seconds')
        for i,p in enumerate(paths,1):
            if self.cancel_requested.is_set():
                cancelled=True;break
            try:
                with Image.open(p) as source:
                    icc=source.info.get('icc_profile') if keep_icc else None
                    exif_bytes=source.getexif().tobytes() if keep_exif and fmt in ('JPEG','WEBP') else None
                    source.seek(0)
                    im=ImageOps.exif_transpose(source).copy()
                im=self.transform(im,w,h,mode,rotation,brightness,contrast,mark,opacity,logo,logo_scale,position)
                if fmt=='JPEG':
                    if im.mode in ('RGBA','LA') or 'transparency' in im.info:
                        base=Image.new('RGB',im.size,'white');base.paste(im,mask=im.getchannel('A') if 'A' in im.getbands() else None);im=base
                    else:im=im.convert('RGB')
                elif im.mode not in ('RGB','RGBA'):im=im.convert('RGBA')
                stem=f'{nstart+i-1:0{ndigits}d}' if numbering else Path(p).stem
                target=self.unique_path(out,prefix+stem+suffix,FORMATS[fmt])
                kw={'quality':quality,'optimize':optimize} if fmt in ('JPEG','WEBP') else {'optimize':optimize}
                kw['dpi']=(dpi,dpi) if fmt in ('JPEG','PNG') else (dpi,dpi)
                if icc:kw['icc_profile']=icc
                # EXIF-orientáció nullázása: a imagepontok már el vannak forgatva.
                if exif_bytes:
                    try:
                        ex=Image.Exif();ex.load(exif_bytes);ex[274]=1
                        kw['exif']=ex.tobytes()
                    except (ValueError,TypeError,KeyError):pass
                if fmt=='WEBP':kw.pop('dpi',None)
                im.save(target,format=fmt,**kw)
                good+=1
                log.append(f'OK | {Path(p).name} → {target.name} | {target.stat().st_size} bájt')
            except (OSError,ValueError,UnidentifiedImageError) as exc:
                bad.append(f'{Path(p).name}: {exc}')
                log.append(f'HIBA | {Path(p).name} | {exc}')
            self.events.put(('progress',i,len(paths),Path(p).name))
        report=out/('imagebatch_naplo_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.txt')
        try:
            report.write_text('ImageBatch Pro 1.0 feldolgozási napló\nKezdés: '+started+'\nBefejezés: '+datetime.now().isoformat(timespec='seconds')+'\nSuccessful: '+str(good)+' | Hibás: '+str(len(bad))+' | Megszakítva: '+str(cancelled)+'\n\n'+'\n'.join(log)+'\n',encoding='utf-8')
        except OSError as exc:
            bad.append('Logsave: '+str(exc))
        self.events.put(('done',good,bad,str(out),cancelled,str(report)))
    def poll(self):
        try:
            while True:
                event=self.events.get_nowait()
                if event[0]=='progress':
                    _,i,n,name=event;self.progress.set(i/n*100);self.status.set(f'{i}/{n}: {name}')
                elif event[0]=='done':
                    _,good,bad,out,cancelled,report=event;self.running=False;self.startbtn.configure(state='normal');self.cancelbtn.configure(state='disabled')
                    self.status.set(f'{"Megszakítva" if cancelled else "Done"}: {good} successful, {len(bad)} hibás. Kimenet: {out}')
                    msg=f'{good} image elkészült.\nKimenet: {out}\nLog: {report}'
                    if bad:msg+='\n\nHibák:\n'+'\n'.join(bad[:15])
                    messagebox.showinfo('Processing kész',msg)
        except queue.Empty:pass
        self.root.after(100,self.poll)

if __name__=='__main__':
    root=tk.Tk()
    try:ttk.Style().theme_use('clam')
    except tk.TclError:pass
    App(root)
    root.mainloop()
