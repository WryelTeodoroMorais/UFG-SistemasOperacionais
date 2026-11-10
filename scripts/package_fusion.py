"""Distribuição independente; sem reescrever entregas anteriores."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FUSION=ROOT/'evolution'/'fusion'
destination=ROOT/'releases/sentinela-fusao-validada.zip'
if destination.exists():
    raise FileExistsError('Use outro nome para nova revisão; pacote preservado')
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0')
files=[ROOT/path.decode() for path in tracked if path]
files.extend(FUSION/'inputs'/sample
             for sample in ('test-100000-8.csv','test-100000-16.csv'))
files=sorted(set(files),key=lambda path:path.as_posix())
manifest={'prepared_at_utc':datetime.now(timezone.utc).isoformat(),
          'scope':'fusion + supervised evaluation',
          'files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
    for p in files:
        archive.write(p,p.relative_to(ROOT))
    archive.writestr('manifest-fusion.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
    for rel,digest in manifest['files'].items():
        assert hashlib.sha256(archive.read(rel)).hexdigest()==digest
print(destination)
print('SHA256',hashlib.sha256(destination.read_bytes()).hexdigest())
