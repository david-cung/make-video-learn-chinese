import sys, pathlib, asyncio, subprocess, json, math, ssl, re, argparse, hashlib
ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT/'tools'))
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
BUILD = ROOT/'source'
BUILD.mkdir(exist_ok=True)
ASSETS = ROOT/'assets'
W,H,FPS = 1080,1920,24
TTS_ENGINE = 'edge'
VIENEU_VOICE = 'Trúc Ly'
OUTPUT_STEM = 'bai-01-ni-hao'
LESSON_TITLE = 'BÀI 01: CHÀO HỎI'
MAX_DURATION = None
SCENES = [
 ('vi','Tiếng Trung mỗi ngày! Hôm nay, cùng học cách chào và hỏi thăm nhé.', 'BẮT ĐẦU TỪ MỘT LỜI CHÀO', '你好', 'nǐ hǎo', 'Xin chào', 'Một lời chào đơn giản để bắt đầu cuộc trò chuyện.'),
 ('vi','Hai chữ này có nghĩa là xin chào. Nhìn phần phiên âm trên màn hình nhé, cả hai âm đều mang dấu thanh ba.', '01 / HIỂU NGHĨA', '你好', 'nǐ hǎo', 'Xin chào', '你 = bạn     •     好 = tốt'),
 ('zh','你好。你好。', '02 / NGHE VÀ NHẮC LẠI', '你好', 'ní hǎo', 'Hãy đọc theo cô nhé!', 'Khi nói liền: thanh 3 + thanh 3 → thanh 2 + thanh 3.'),
 ('vi','Lưu ý nhé: khi hai thanh ba đứng liền nhau, âm đầu thường đọc thành thanh hai. Cách viết phiên âm vẫn giữ nguyên. Cùng nghe và luyện lại nhé!', 'MẸO PHÁT ÂM', '你好', 'nǐ hǎo → ní hǎo', 'Viết thanh 3 • đọc âm đầu thành thanh 2', 'Nghe mẫu, rồi nói chậm và rõ.'),
 ('zh','你好！你好吗？', '03 / THỬ MỘT CÂU NGẮN', '你好吗？', 'nǐ hǎo ma?', 'Bạn khỏe không?', 'Thêm 吗 ở cuối để tạo câu hỏi trong ví dụ này.'),
 ('vi','Câu vừa rồi có nghĩa là: bạn khỏe không? Bạn có thể trả lời: tôi rất khỏe, cảm ơn.', '04 / CÁCH TRẢ LỜI', '我很好，谢谢！', 'wǒ hěn hǎo, xièxie!', 'Tôi rất khỏe, cảm ơn!', 'Một cuộc hội thoại ngắn để luyện mỗi ngày.'),
 ('zh','我很好，谢谢！', 'NGHE THÊM MỘT LẦN', '我很好，谢谢！', 'wǒ hěn hǎo, xièxie!', 'Tôi rất khỏe, cảm ơn!', 'Đến lượt bạn: dừng một nhịp và đọc theo.'),
 ('vi','Bây giờ, hãy tự chào bằng tiếng Trung nhé! Luyện một câu mỗi ngày, bạn sẽ tự tin hơn. Hẹn gặp lại ở bài tiếp theo!', 'NHỚ MỘT CÂU HÔM NAY', '你好！', 'nǐ hǎo!', 'Xin chào!', 'Nghe → nhắc lại → dùng trong một tình huống thật.'),
]

def run(args, **kw):
    return subprocess.run([FF,'-hide_banner','-loglevel','error',*args],check=True,**kw)

def edge_voice_path(i,lang,text):
    # Keep the original Chinese takes; key new Vietnamese audio by its text.
    suffix='-'+hashlib.sha256((lang+text).encode('utf-8')).hexdigest()[:12]
    if lang=='zh' and text==SCENES[i][1] and BUILD==ROOT/'source':
        legacy=BUILD/f'voice-{i}.mp3'
        if legacy.exists(): return legacy
    return BUILD/f'voice-{i}{suffix}.mp3'

async def voices():
    if TTS_ENGINE == 'vieneu':
        manifest = BUILD/'vieneu-script.json'
        manifest.write_text(json.dumps([{'index':i,'text':s[1]} for i,s in enumerate(SCENES) if s[0]=='vi'],ensure_ascii=False),encoding='utf-8')
        subprocess.run([str(ROOT/'.venv-vieneu/Scripts/python.exe'),str(ROOT/'vieneu_narration.py'),'--manifest',str(manifest),'--voice',VIENEU_VOICE,'--output-dir',str(BUILD/'vieneu')],check=True)
    import edge_tts, aiohttp, certifi
    certifi.where = lambda: str(ROOT/'windows-ca.pem')
    # Keep TLS verification enabled and use the Windows certificate authorities.
    ctx = ssl.create_default_context(cafile=str(ROOT/'windows-ca.pem'))
    for i,(lang,text,*_) in enumerate(SCENES):
        if lang == 'vi' and TTS_ENGINE == 'vieneu': continue
        target=edge_voice_path(i,lang,text)
        if target.exists() and target.stat().st_size>1000: continue
        print(f'Voice {i+1}/{len(SCENES)}',flush=True)
        for attempt in range(6):
            try:
                async with aiohttp.TCPConnector(ssl=ctx) as connector:
                    voice='zh-CN-XiaoxiaoNeural' if lang=='zh' else 'vi-VN-HoaiMyNeural'
                    await edge_tts.Communicate(text,voice,rate='-8%',connector=connector).save(str(target))
                break
            except Exception:
                if attempt==5: raise
                print('Voice service busy; retrying shortly',flush=True)
                await asyncio.sleep(8*(attempt+1))
        await asyncio.sleep(4)

def font(size,zh=False,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/'+('msyhbd.ttc' if zh else 'arialbd.ttf' if bold else 'arial.ttf'),size)

def centered(d,text,y,size,color,zh=False,bold=False):
    runs=re.findall(r'[\u3400-\u9fff，。！？、]+|[^\u3400-\u9fff，。！？、]+',text)
    def pieces(s):
        return [(r,font(s,bool(re.search(r'[\u3400-\u9fff，。！？、]',r)),bold)) for r in runs]
    parts=pieces(size)
    while sum(d.textlength(r,font=f) for r,f in parts)>940:
        size-=2; parts=pieces(size)
    x=(W-sum(d.textlength(r,font=f) for r,f in parts))/2
    for r,f in parts:
        d.text((x,y+size),r,font=f,fill=color,anchor='ls')
        x+=d.textlength(r,font=f)

def wrap(d,text,y,size,color,width=900):
    f=font(size); lines=[]; line=''
    for word in text.split():
        proposed=(line+' '+word).strip()
        if d.textlength(proposed,font=f)>width and line: lines.append(line); line=word
        else: line=proposed
    if line: lines.append(line)
    for line in lines:
        centered(d,line,y,size,color); y+=size+14
    return y

def render():
    durations=[]; srt=[]; clock=0
    for i,(lang,text,label,han,pinyin,meaning,note) in enumerate(SCENES):
        raw=BUILD/f'audio-{i}.wav'
        voice_path = BUILD/'vieneu'/f'voice-{i}.wav' if lang=='vi' and TTS_ENGINE=='vieneu' else edge_voice_path(i,lang,text)
        run(['-y','-i',str(voice_path),'-ar','48000','-ac','1',str(raw)])
        import wave
        with wave.open(str(raw),'rb') as wav: spoken=wav.getnframes()/wav.getframerate()
        duration=math.ceil((spoken+1.0)*FPS)/FPS
        if MAX_DURATION is not None and clock+duration>MAX_DURATION:
            raise ValueError('Kịch bản vượt thời lượng tối đa. Hãy rút gọn lời đọc.')
        durations.append(duration)
        base=Image.new('RGB',(W,H),'#f7f2e8'); d=ImageDraw.Draw(base)
        d.rounded_rectangle((54,62,1026,170),radius=36,fill='#143f3b')
        centered(d,'TIẾNG TRUNG • MỖI NGÀY MỘT CHÚT',92,34,'#ffffff',bold=True)
        centered(d,label,222,35,'#46766a',bold=True)
        d.rounded_rectangle((54,319,1026,895),radius=42,fill='#ffffff',outline='#dedbcf',width=2)
        centered(d,han,380,138,'#143f3b',zh=True)
        centered(d,pinyin,577,61,'#b44a32')
        centered(d,meaning,696,43,'#143f3b',bold=True)
        wrap(d,note,785,30,'#64756c')
        d.ellipse((354,1405,740,1475),fill='#dfdfd1')
        d.rounded_rectangle((54,1510,1026,1775),radius=34,fill='#143f3b')
        centered(d,'LỜI GIẢNG' if lang=='vi' else 'PHÁT ÂM MẪU',1540,26,'#e4bd77',bold=True)
        # Split long narration into timed caption cards for readable subtitles.
        chunks=re.split(r'(?<=[.!?。！？])\s*',text); chunks=[x for x in chunks if x]
        caption=text
        if len(text)>150:
            words=text.split(); caption=' '.join(words[:26])+'…'
        for mouth in (0,1):
            frame=base.copy()
            teacher=Image.open(ASSETS/('co-giao-noi.webp' if mouth else 'co-giao.webp')).convert('RGBA')
            teacher.thumbnail((530,570),Image.Resampling.LANCZOS)
            frame.paste(teacher,((W-teacher.width)//2,930+(550-teacher.height)),teacher)
            frame.save(BUILD/f'base-{i}-{mouth}.png')
        # Render caption pages per sentence, timed proportionally to text length.
        frames=[]
        for m in (0,1): frames.append(Image.open(BUILD/f'base-{i}-{m}.png').convert('RGB'))
        proc=subprocess.Popen([FF,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(raw),'-af','apad','-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(BUILD/f'part-{i}.mp4')],stdin=subprocess.PIPE)
        weights=[len(c) for c in chunks]; total=sum(weights); boundaries=[]; elapsed=0
        for chunk,weight in zip(chunks,weights):
            end=elapsed+spoken*weight/total; boundaries.append((end,chunk))
            def stamp(t):
                ms=round(t*1000); return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
            srt.append(f'{len(srt)+1}\n{stamp(clock+elapsed)} --> {stamp(clock+end)}\n{chunk}\n')
            elapsed=end
        cached={}
        for n in range(round(duration*FPS)):
            t=n/FPS; idx=next((j for j,(end,_) in enumerate(boundaries) if t<end),len(boundaries)-1)
            mouth=int(t*6)%2 if t<spoken else 0
            key=(idx,mouth)
            if key not in cached:
                im=frames[mouth].copy(); di=ImageDraw.Draw(im)
                wrap(di,boundaries[idx][1],1596,36,'#ffffff')
                centered(di,f'{i+1:02} / {len(SCENES):02}    •    {LESSON_TITLE}',1825,28,'#64756c')
                cached[key]=im
            im=cached[key].copy(); di=ImageDraw.Draw(im)
            di.rounded_rectangle((54,1880,1026,1888),radius=4,fill='#dedbcf')
            di.rounded_rectangle((54,1880,54+max(1,int(972*(i+t/duration)/len(SCENES))),1888),radius=4,fill='#b44a32')
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        if proc.wait()!=0: raise RuntimeError('Video encoding failed')
        clock+=duration; print(f'Rendered scene {i+1}: {duration:.1f}s',flush=True)
    (BUILD/'concat.txt').write_text('\n'.join(f"file 'part-{i}.mp4'" for i in range(len(SCENES))))
    run(['-y','-f','concat','-safe','0','-i',str(BUILD/'concat.txt'),'-c','copy','-movflags','+faststart',str(ROOT/f'{OUTPUT_STEM}.mp4')])
    (ROOT/f'{OUTPUT_STEM}.srt').write_text('\n'.join(srt),encoding='utf-8-sig')
    (ROOT/'kich-ban.txt').write_text('\n\n'.join(f'{i+1}. {s[2]}\n{s[3]} | {s[4]} | {s[5]}\nLời đọc: {s[1]}' for i,s in enumerate(SCENES)),encoding='utf-8')
    (ROOT/f'{OUTPUT_STEM}-info.json').write_text(json.dumps({'duration_seconds':clock,'width':W,'height':H,'fps':FPS,'video':'H.264','audio':'AAC','voices':[f'VieNeu-TTS / {VIENEU_VOICE}' if TTS_ENGINE=='vieneu' else 'vi-VN-HoaiMyNeural','zh-CN-XiaoxiaoNeural'],'assets':str(ASSETS)},indent=2,ensure_ascii=False),encoding='utf-8')
    Image.open(BUILD/'base-0-0.png').save(ROOT/'anh-bia.jpg',quality=92)
    print(f'DONE: {clock:.2f}s',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--tts',choices=['edge','vieneu'],default='edge')
    parser.add_argument('--voice',default='Trúc Ly')
    args=parser.parse_args()
    TTS_ENGINE=args.tts
    VIENEU_VOICE=args.voice
    if TTS_ENGINE=='vieneu': OUTPUT_STEM='bai-01-ni-hao-vieneu'
    asyncio.run(voices())
    render()
