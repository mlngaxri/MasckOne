from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'website/index.html'
EXPECTED='02233ffae09c93df0f46ba056bdb8dd01d8975c7'

def blob_sha(data:bytes)->str:
    h=hashlib.sha1(); h.update(f'blob {len(data)}\0'.encode()); h.update(data); return h.hexdigest()

def once(s,old,new,label):
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'{label}: expected 1 match, got {n}')
    return s.replace(old,new,1)

raw=INDEX.read_bytes(); sha=blob_sha(raw)
if sha!=EXPECTED:
    raise RuntimeError(f'unexpected website baseline {sha}')
s=raw.decode()

old='''/* Persistent navigation + visible earth-tone shader */
.header{overflow:hidden;opacity:1;pointer-events:auto;clip-path:none;transform:translateX(-50%);border:2px solid transparent;background:linear-gradient(rgba(248,250,248,.82),rgba(248,250,248,.76)) padding-box,linear-gradient(112deg,#f6f1e8 0%,#738267 20%,#b97e65 42%,#8fa6a2 64%,#c7b28f 82%,#f6f1e8 100%) border-box;background-size:100% 100%,260% 100%;background-position:0 0,0% 50%;backdrop-filter:blur(18px) saturate(1.08);box-shadow:0 14px 42px rgba(24,33,28,.075),inset 0 1px 0 rgba(255,255,255,.38);animation:navShader 12s ease-in-out infinite alternate}
.header>*{opacity:1}
.nav-progress{left:2px;right:2px;bottom:2px;height:3px;border-radius:0 0 999px 999px;background:rgba(24,33,28,.07)}
.nav-progress-fill{background:#738267;box-shadow:0 0 9px rgba(115,130,103,.38)}
'''
new='''/* Persistent navigation, intentionally outline-free */
.header{overflow:hidden;opacity:1;pointer-events:auto;clip-path:none;transform:translateX(-50%);border:0;background:rgba(248,250,248,.78);backdrop-filter:blur(18px) saturate(1.08);box-shadow:0 14px 42px rgba(24,33,28,.07),inset 0 1px 0 rgba(255,255,255,.34);animation:none}
.header>*{opacity:1}
.nav-progress{left:0;right:0;bottom:0;height:3px;border-radius:0 0 999px 999px;background:rgba(24,33,28,.07)}
.nav-progress-fill{background:#738267;box-shadow:0 0 9px rgba(115,130,103,.30)}
'''
s=once(s,old,new,'remove navbar outline shader')
INDEX.write_text(s)
print('refined', blob_sha(INDEX.read_bytes()))
