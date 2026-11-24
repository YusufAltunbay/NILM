"""UK-DALE HDF5 dosyasını data/raw/ altına indirir ve MD5 ile doğrular.

Kaynak: Zenodo kaydı 13917372 (NILMTK biçiminde ukdale.h5, ~3.35 GB).
Yarıda kalan indirme yeniden çalıştırınca kaldığı yerden devam eder.
Kullanım: python -m scripts.download_ukdale
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

URL = "https://zenodo.org/api/records/13917372/files/ukdale.h5/content"
MD5 = "57a1ad0478e9dc80ab5dc1050573590c"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "ukdale.h5"


def md5sum(path, chunk=1 << 22):
    h = hashlib.md5()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def download():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    part = OUT.with_suffix(".h5.part")
    start = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(URL, headers={"Range": f"bytes={start}-"} if start else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        if start and r.status != 206:  # sunucu devam desteklemiyorsa baştan indir
            start = 0
        with part.open("ab" if start else "wb") as f:
            _copy(r, f, start)
    part.replace(OUT)


def _copy(r, f, start):
    total = start + int(r.headers.get("Content-Length", 0))
    done = start
    while b := r.read(1 << 20):
        f.write(b)
        done += len(b)
        if done % (100 << 20) < (1 << 20):
            print(f"{done / 1e9:.2f} / {total / 1e9:.2f} GB", flush=True)


if __name__ == "__main__":
    if not OUT.exists():
        download()
    got = md5sum(OUT)
    if got != MD5:
        sys.exit(f"MD5 uyuşmuyor: {got} (beklenen {MD5})")
    print(f"Tamam: {OUT}")
