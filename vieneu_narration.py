"""Generate the Vietnamese narration in a separate, reproducible CPU environment."""
import argparse
import hashlib
import json
import os
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8',errors='replace')
sys.stderr.reconfigure(encoding='utf-8',errors='replace')

ROOT=pathlib.Path(__file__).parent
os.environ.setdefault('HF_HOME',str(ROOT/'models'))
os.environ.setdefault('HF_HUB_DISABLE_XET','1')
os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT','120')
os.environ.setdefault('HF_HUB_ETAG_TIMEOUT','30')
os.environ.setdefault('SSL_CERT_FILE',str(ROOT/'windows-ca.pem'))
os.environ.setdefault('REQUESTS_CA_BUNDLE',str(ROOT/'windows-ca.pem'))
# Reuse the fully downloaded, pinned model without checking remote metadata.
model_cache=ROOT/'models/hub/models--pnnbao-ump--VieNeu-TTS-v3-Turbo'
codec_cache=ROOT/'models/hub/models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX'
required_model=['config.json','tokenizer.json','vieneu_prefill.onnx','vieneu_decode_step.onnx','vieneu_acoustic_cached.onnx','vieneu_backbone_shared.data','vieneu_v3_heads.npz']
required_codec=['moss_audio_tokenizer_decode_full.onnx','moss_audio_tokenizer_decode_shared.data','moss_audio_tokenizer_decode_step.onnx','codec_browser_onnx_meta.json','moss_audio_tokenizer_encode.onnx','moss_audio_tokenizer_encode.data']
if all(any(model_cache.glob(f'snapshots/*/onnx_update/{name}')) for name in required_model) and all(any(codec_cache.glob(f'snapshots/*/{name}')) for name in required_codec):
    os.environ.setdefault('HF_HUB_OFFLINE','1')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=pathlib.Path,required=True)
    parser.add_argument('--voice',default='Trúc Ly')
    parser.add_argument('--output-dir',type=pathlib.Path,default=ROOT/'source/vieneu')
    args=parser.parse_args()
    from vieneu import Vieneu
    import numpy as np
    import soundfile as sf
    from importlib.metadata import version
    destination=args.output_dir
    destination.mkdir(parents=True,exist_ok=True)
    items=json.loads(args.manifest.read_text(encoding='utf-8'))
    print('Loading VieNeu-TTS on CPU (ONNX)...',flush=True)
    tts=Vieneu(backend='onnx')
    available=tts.list_preset_voices()
    print('Preset voices:',available,flush=True)
    if tts.resolve_voice_name(args.voice) is None:
        raise ValueError(f'Voice not available: {args.voice}')
    for item in items:
        path=destination/f"voice-{item['index']}.wav"
        meta=path.with_suffix('.json')
        signature={'text':item['text'],'voice':args.voice,'engine':'vieneu','version':version('vieneu')}
        if path.exists() and meta.exists() and json.loads(meta.read_text(encoding='utf-8'))==signature:
            sf.info(path)
            continue
        print(f"Synthesizing Vietnamese scene {item['index']+1}...",flush=True)
        audio=tts.infer(item['text'],voice=args.voice)
        if len(audio)==0 or not np.isfinite(audio).all() or np.max(np.abs(audio))<0.001:
            raise ValueError('Invalid or silent generated audio')
        temp=path.with_name(path.stem+'.tmp.wav')
        tts.save(audio,str(temp))
        info=sf.info(temp)
        if info.duration<1: raise ValueError('Generated narration is too short')
        temp.replace(path)
        meta.write_text(json.dumps(signature,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'Saved {path.name}: {info.duration:.2f}s / {info.samplerate} Hz',flush=True)

if __name__=='__main__': main()
