"""Private local benchmark on your own WAV recordings; prints texts to the terminal only."""
import argparse
import statistics
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ivt.config import Config
from ivt.engine import Engine

def vram_mib():
    try:
        out=subprocess.run(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10)
        return int(out.stdout.split()[0])
    except Exception:
        return None

def p95(values):
    values=sorted(values)
    return values[min(len(values)-1,round(0.95*(len(values)-1)))]

parser=argparse.ArgumentParser()
parser.add_argument('audio',nargs='+',help='WAV files or folders with local recordings; never committed')
parser.add_argument('--device',choices=['cpu','cuda','auto'],default='auto')
parser.add_argument('--download',action='store_true')
parser.add_argument('--engine',choices=['direct','two-stage','both'],default='both')
parser.add_argument('--models',nargs='+',default=['small','medium','large-v3'])
parser.add_argument('--repeats',type=int,default=3)
parser.add_argument('--names',default='',help='Comma-separated vocabulary (tracks, corners, nicknames)')
args=parser.parse_args()
files=sorted(f for a in args.audio for f in ([Path(a)] if Path(a).is_file() else Path(a).glob('*.wav')))
engines=['direct','two-stage'] if args.engine=='both' else [args.engine]
summary=[]
for mode in engines:
    for model in args.models:
        before=vram_mib()
        engine=Engine(Config(model=model,device=args.device,engine=mode))
        start=time.perf_counter();engine.load(args.download);load_s=time.perf_counter()-start
        loaded=vram_mib()
        if engine.warning:print('WARNING:',engine.warning)
        names=[n for n in args.names.split(',') if n.strip()]
        engine.process(str(files[0]),names)  # warm-up
        speech,translation,total=[],[],[]
        for path in files:
            for repeat in range(args.repeats):
                start=time.perf_counter()
                source,output,times=engine.process(str(path),names)
                total.append(time.perf_counter()-start);speech.append(times['speech_s']);translation.append(times['translation_s'])
            print(f'[{mode} {model}] {path.name}: {source!r} -> {output!r}' if mode=='two-stage' else f'[{mode} {model}] {path.name}: {output!r}')
        row=dict(engine=mode,model=model,device=engine.actual_device,load_s=load_s,
                 median_s=statistics.median(total),p95_s=p95(total),speech_median_s=statistics.median(speech),
                 translation_median_s=statistics.median(translation),
                 vram_mib=(loaded-before) if before is not None and loaded is not None else None)
        summary.append(row);print(row,flush=True)
        del engine
print('\n| Wariant | Model | Urządzenie | Mediana | p95 | Rozpoznawanie (med.) | Marian (med.) | VRAM po załadowaniu |')
print('|---|---|---|---:|---:|---:|---:|---:|')
for r in summary:
    print(f"| {'A direct' if r['engine']=='direct' else 'B two-stage'} | {r['model']} | {r['device']} | {r['median_s']:.2f} s | {r['p95_s']:.2f} s | "
          f"{r['speech_median_s']:.2f} s | {r['translation_median_s']:.2f} s | {r['vram_mib'] if r['vram_mib'] is not None else '?'} MiB |")
