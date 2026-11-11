import os, sys, pathlib, json, asyncio
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
sys.stderr.reconfigure(encoding='utf-8',errors='replace')
from lesson_planner import validate
import make_video as renderer

def main():
    folder=pathlib.Path(sys.argv[1]).resolve()
    plan=validate(json.loads((folder/'script.json').read_text(encoding='utf-8')))
    renderer.BUILD=folder/'work'
    renderer.BUILD.mkdir(exist_ok=True)
    renderer.ROOT=folder
    renderer.ASSETS=pathlib.Path(__file__).parent/'assets'
    renderer.LESSON_TITLE=plan['title'].upper()
    renderer.TTS_ENGINE='vieneu'
    renderer.VIENEU_VOICE=plan.get('voice','Trúc Ly')
    renderer.OUTPUT_STEM='video'
    renderer.MAX_DURATION=40
    renderer.SCENES=[tuple(s[k] for k in ['lang','text','label','hanzi','pinyin','meaning','note']) for s in plan['scenes']]
    # ROOT remains the application folder during audio generation (venv/certs).
    output=renderer.ROOT
    renderer.ROOT=pathlib.Path(__file__).parent
    asyncio.run(renderer.voices())
    renderer.ROOT=output
    renderer.render()

if __name__=='__main__': main()
