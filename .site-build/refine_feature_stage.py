from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'website/index.html'
EXPECTED='c0cf08bc354d08187d908cd3ec66c22b563a7863'

def blob_sha(data:bytes)->str:
    h=hashlib.sha1(); h.update(f'blob {len(data)}\0'.encode()); h.update(data); return h.hexdigest()

def once(s,old,new,label):
    n=s.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected 1 match, got {n}')
    return s.replace(old,new,1)

raw=INDEX.read_bytes(); sha=blob_sha(raw)
if sha!=EXPECTED: raise RuntimeError(f'unexpected website baseline {sha}')
s=raw.decode()
s=once(s,'<section class="view" data-view="system" aria-label="System section">','<section class="view" data-view="system" aria-label="Systems section">','systems aria label')
s=once(s,'<div class="section-tag"><span>System</span><b>01 / 02</b></div>','<div class="section-tag"><span>Systems</span><b>01 / 02</b></div>','systems first tag')
s=once(s,'<div class="section-tag"><span>System</span><b>02 / 02</b></div>','<div class="section-tag"><span>Systems</span><b>02 / 02</b></div>','systems second tag')
s=once(s,'<div class="page-index">02 / System / 01</div>','<div class="page-index">02 / Systems / 01</div>','systems first index')
s=once(s,'<div class="page-index">02 / System / 02</div>','<div class="page-index">02 / Systems / 02</div>','systems second index')
INDEX.write_text(s)
print('refined',blob_sha(INDEX.read_bytes()))
