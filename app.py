"""Local-only video studio. Run with the base Python used for make_video.py."""
import http.server, json, pathlib, mimetypes, threading, queue, uuid, subprocess, sys, re, os, time
from urllib.parse import urlparse, unquote
from lesson_planner import plan_topic,validate
ROOT=pathlib.Path(__file__).parent
OUTPUTS=ROOT/'outputs'
OUTPUTS.mkdir(exist_ok=True)
JOBS={}
LOCK=threading.Lock()
WORK=queue.Queue(maxsize=2)
ACTIVE_PROCESS=None
VOICES=['Trúc Ly','Ngọc Huyền','Mai Anh','Thùy Dung']

def update(job_id,**fields):
    with LOCK:
        JOBS[job_id].update(fields)
        (OUTPUTS/job_id/'status.json').write_text(json.dumps(JOBS[job_id],ensure_ascii=False,indent=2),encoding='utf-8')

def worker():
    global ACTIVE_PROCESS
    while True:
        job_id=WORK.get()
        try:
            folder=OUTPUTS/job_id
            update(job_id,status='running',progress=8,message='Đang tạo giọng Việt bằng VieNeu…')
            env=os.environ.copy(); env['PYTHONIOENCODING']='utf-8'
            proc=subprocess.Popen([sys.executable,'-u',str(ROOT/'render_job.py'),str(folder)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
            ACTIVE_PROCESS=proc
            lines=[]
            for line in proc.stdout:
                lines.append(line)
                if 'Saved voice-' in line: update(job_id,progress=25,message='Đã tạo lời giảng Việt, đang xử lý các cảnh tiếp theo…')
                if 'Voice ' in line: update(job_id,progress=38,message='Đang đọc chữ Hán bằng giọng Trung…')
                match=re.search(r'Rendered scene (\d+):',line)
                if match:
                    count=JOBS[job_id]['scenes']
                    n=int(match[1]);update(job_id,progress=45+int(50*n/count),message=f'Đang dựng cảnh {n}/{count}…')
            code=proc.wait()
            (folder/'render.log').write_text(''.join(lines),encoding='utf-8')
            if code: raise RuntimeError('Tạo video chưa thành công. Hãy kiểm tra kết nối mạng hoặc rút gọn kịch bản và thử lại. Chi tiết trong render.log của video.')
            info=json.loads((folder/'video-info.json').read_text(encoding='utf-8'))
            update(job_id,status='done',progress=100,message='Video đã sẵn sàng.',duration=round(info['duration_seconds'],1),video=f'/outputs/{job_id}/video.mp4',poster=f'/outputs/{job_id}/anh-bia.jpg',subtitles=f'/outputs/{job_id}/video.srt')
        except Exception as exc:
            update(job_id,status='error',message=str(exc),progress=0)
        finally:
            ACTIVE_PROCESS=None
            WORK.task_done()

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def json(self,status,data):
        raw=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=unquote(urlparse(self.path).path)
        if path=='/api/jobs':
            with LOCK: items=[dict(v) for v in JOBS.values()]
            return self.json(200,sorted(items,key=lambda x:x.get('created',0),reverse=True))
        if path=='/api/config': return self.json(200,{'voices':VOICES,'vieNeuReady':(ROOT/'.venv-vieneu/Scripts/python.exe').exists(),'topics':['Chào hỏi','Gọi cà phê','Cảm ơn','Gọi món ở nhà hàng','Đi taxi ra sân bay','Cách học từ vựng']})
        if path in ('/','/app.js','/style.css'):
            file=ROOT/'web'/('index.html' if path=='/' else path[1:])
        elif re.fullmatch(r'/outputs/[0-9a-f]{32}/(video\.mp4|anh-bia\.jpg|video\.srt|script\.json)',path): file=ROOT/path.lstrip('/')
        elif path in ('/assets/co-giao.webp','/assets/co-giao-noi.webp'): file=ROOT/path[1:]
        else: return self.json(404,{'error':'Không tìm thấy.'})
        if not file.is_file(): return self.json(404,{'error':'File chưa sẵn sàng.'})
        size=file.stat().st_size; start=0;end=size-1;status=200
        request_range=self.headers.get('Range')
        if request_range:
            m=re.fullmatch(r'bytes=(\d*)-(\d*)',request_range)
            if not m: return self.json(416,{'error':'Khoảng dữ liệu không hợp lệ.'})
            if not m[1]: start=max(0,size-int(m[2] or 0))
            else: start=int(m[1]);end=min(size-1,int(m[2])) if m[2] else size-1
            if start>end or start>=size: return self.json(416,{'error':'Khoảng dữ liệu không hợp lệ.'})
            status=206
        self.send_response(status);self.send_header('Content-Type',mimetypes.guess_type(file.name)[0] or 'application/octet-stream');self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes');self.send_header('X-Content-Type-Options','nosniff')
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with file.open('rb') as f:
                f.seek(start);left=end-start+1
                while left:
                    data=f.read(min(left,65536))
                    if not data: break
                    self.wfile.write(data);left-=len(data)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError): pass
    def do_POST(self):
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://{self.headers.get("Host")}': return self.json(403,{'error':'Chỉ dùng ứng dụng từ máy này.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=65536: raise ValueError('Dữ liệu quá dài hoặc trống.')
            data=json.loads(self.rfile.read(length))
            if self.path=='/api/plan': return self.json(200,plan_topic(data.get('topic')))
            if self.path=='/api/jobs':
                plan=validate(data)
                voice=plan.get('voice','Trúc Ly')
                if voice not in VOICES: raise ValueError('Giọng Việt chưa được hỗ trợ.')
                plan['voice']=voice
                with LOCK:
                    if sum(j['status'] in ('queued','running') for j in JOBS.values())>=2: return self.json(409,{'error':'Đang có hai video chờ xử lý. Vui lòng chờ video hiện tại hoàn tất.'})
                    job_id=uuid.uuid4().hex;folder=OUTPUTS/job_id;folder.mkdir()
                    (folder/'script.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
                    JOBS[job_id]={'id':job_id,'title':plan['title'],'created':time.time(),'scenes':len(plan['scenes']),'status':'queued','progress':0,'message':'Đang chờ đến lượt…'}
                    result=dict(JOBS[job_id])
                    (folder/'status.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
                    WORK.put_nowait(job_id)
                return self.json(202,result)
            return self.json(404,{'error':'Không tìm thấy.'})
        except (ValueError,TypeError,AttributeError,KeyError) as exc: return self.json(400,{'error':str(exc)})

def serve(port=3015,open_browser=False):
    for f in OUTPUTS.glob('*/status.json'):
        try:
            job=json.loads(f.read_text(encoding='utf-8'))
            if job['status'] in ('queued','running'):
                job.update(status='error',progress=0,message='Lượt tạo trước bị ngắt khi đóng app. Hãy tạo lại video.')
            JOBS[job['id']]=job
        except (ValueError,KeyError): pass
    threading.Thread(target=worker,daemon=True).start()
    server=http.server.ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Chinese Short Studio: http://127.0.0.1:{port}',flush=True)
    if open_browser:
        import webbrowser
        threading.Timer(0.7,lambda:webbrowser.open(f'http://127.0.0.1:{port}')).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        server.server_close()
        if ACTIVE_PROCESS and ACTIVE_PROCESS.poll() is None:
            if os.name=='nt': subprocess.run(['taskkill','/PID',str(ACTIVE_PROCESS.pid),'/T','/F'],capture_output=True)
            else: ACTIVE_PROCESS.terminate()

if __name__=='__main__': serve(int(os.environ.get('PORT','3015')),'--open' in sys.argv)
