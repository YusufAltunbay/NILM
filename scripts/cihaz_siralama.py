"""UK-DALE'deki tüm cihazları toplam enerjideki paya ve ev kapsamına göre sıralar.

Çıktı: results/cihaz_siralama.csv ve ekrana özet.
Pay = cihaz enerjisi / evin toplam enerjisi.
- Sürekli kayıt alan sayaçlar (kapsam >= %50): yalnızca cihaz ve toplam sayacın birlikte ölçüldüğü anlarda.
- Seyrek sayaçlar (kapsam < %50; ütü, süpürge, saç kurutma gibi yalnızca cihaz çalışırken kayıt alanlar):
  kayıt olmayan anlar "kapalı" (0 W) sayılır; aksi hâlde yalnızca açık anlar toplama oranlanır ve pay şişer.
Birden fazla sayacı olan cihazlar (örn. 15 lamba sayacı) toplanır; birden fazla cihazın
paylaştığı sayaçlar ("grup sayacı") ayrıca işaretlenir, çünkü cihaz ayrıştırılamaz.
Kullanım: python -m scripts.cihaz_siralama
"""
import collections
from pathlib import Path

import numpy as np
import pandas as pd
import tables

from nilm import config
from nilm.data import ukdale

OUT = Path(__file__).resolve().parents[1] / "results" / "cihaz_siralama.csv"
HOUSES = [1, 2, 5]  # eğitim, test, doğrulama evleri (ev 3 ve 4 çok kısa / grup sayaçlı)
PERIOD = f"{config.SAMPLE_PERIOD_S}s"


def metadata(h5):
    """{ev: [(tip, [sayaçlar]), ...]}; sayaç 0 = ölçülmemiş."""
    out = {}
    for n in sorted(h5.root._v_children):
        meta = h5.get_node("/" + n)._v_attrs["metadata"]
        out[int(n.removeprefix("building"))] = [(a["type"], a["meters"]) for a in meta["appliances"]]
    return out


def main():
    rows = []
    with tables.open_file(str(ukdale.DEFAULT_PATH), "r") as h5:
        meta = metadata(h5)
        for house in HOUSES:
            agg = ukdale._read_power(h5, house, 1).resample(PERIOD).mean()
            users = collections.defaultdict(set)  # sayaç -> o sayaçtaki cihaz tipleri
            for typ, ms in meta[house]:
                for m in ms:
                    users[m].add(typ)
            by_type = collections.defaultdict(set)
            for typ, ms in meta[house]:
                by_type[typ] |= {m for m in ms if m != 0}
            for typ, ms in by_type.items():
                if not ms:
                    continue
                shared = any(len(users[m]) > 1 for m in ms)
                tot = None
                for m in sorted(ms):
                    s = ukdale._read_power(h5, house, m).resample(PERIOD).mean()
                    tot = s if tot is None else tot.add(s, fill_value=0)
                span = agg.loc[tot.dropna().index.min():tot.dropna().index.max()].dropna()
                if len(span) == 0:
                    continue
                both = span.index.intersection(tot.dropna().index)
                coverage = len(both) / len(span)
                if coverage >= 0.5:
                    share, method = tot[both].sum() / span[both].sum(), "sürekli"
                    mean_w = tot[both].mean()
                else:
                    share, method = tot.reindex(span.index).fillna(0).sum() / span.sum(), "seyrek"
                    mean_w = tot.reindex(span.index).fillna(0).mean()
                rows.append(dict(house=house, type=typ, share=share, mean_w=mean_w, coverage=coverage,
                                 method=method, meters=len(ms), shared=shared,
                                 days=len(span) * config.SAMPLE_PERIOD_S / 86400))
            print(f"ev {house} tamam", flush=True)
    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print("yazıldı:", OUT)


if __name__ == "__main__":
    main()
