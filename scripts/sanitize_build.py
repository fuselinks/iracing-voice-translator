"""Remove local compilation paths from collected third-party bytecode."""
from pathlib import Path
import marshal
import types
import sys

def sanitize(code):
    if not isinstance(code,types.CodeType):return code
    filename=code.co_filename.replace('\\','/')
    if ':/' in filename or filename.startswith('/'):
        filename='bundled/'+filename.rsplit('/',1)[-1]
    return code.replace(co_filename=filename,co_consts=tuple(sanitize(value) for value in code.co_consts))

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'dist'/'iRacingVoiceTranslator'
count=0
for path in root.rglob('*.pyc'):
    payload=path.read_bytes()
    path.write_bytes(payload[:16]+marshal.dumps(sanitize(marshal.loads(payload[16:]))))
    count+=1
print('Sanitized collected bytecode files:',count)
