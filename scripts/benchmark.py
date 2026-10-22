"""Private local benchmark; does not save audio or text unless explicitly redirected."""
import argparse
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ivt.config import Config
from ivt.engine import Engine

parser=argparse.ArgumentParser()
parser.add_argument('audio',help='Local Polish speech recording; never committed')
parser.add_argument('--device',choices=['cpu','cuda','auto'],default='auto')
parser.add_argument('--download',action='store_true')
parser.add_argument('--engine',choices=['direct','two-stage'],default='direct')
parser.add_argument('--repeats',type=int,default=3)
args=parser.parse_args()
for model in ['small','medium','large-v3']:
    engine=Engine(Config(model=model,device=args.device,engine=args.engine))
    try:
        engine.load(args.download)
        engine.process(args.audio) # warm-up
        for repeat in range(args.repeats):
            start=time.perf_counter()
            source,output,times=engine.process(args.audio)
            print(model,engine.actual_device,repeat+1,times,'total_s',round(time.perf_counter()-start,3))
            print(output)
    finally:
        del engine
