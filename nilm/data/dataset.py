"""seq2point için bellek dostu PyTorch Dataset'i.

prep.windows() tüm pencereleri bellekte tutar (ev 1'de ~24 GB). Burada yalnızca
normalleştirilmiş 1 boyutlu sinyal tutulur; pencere __getitem__ içinde kesilir.

Kullanım:
    train, val, test, norm = make_datasets("fridge", window=599, stride=1)
    loader = torch.utils.data.DataLoader(train, batch_size=256, shuffle=True)
    for x, y in loader:   # x: (B, 599) normalleştirilmiş toplam, y: (B,) normalleştirilmiş cihaz
        ...
    watts = norm.y_inverse(pred)   # tahmini Watt'a çevirir
"""
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from nilm import config
from nilm.data import prep

PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"


class WindowDataset(Dataset):
    """Pencere i: toplam[s:s+window] -> pencere ortasındaki cihaz gücü.

    Pencereler ev/cihaz sınırlarını ve zaman boşluklarını aşmaz (prep.windows ile aynı kural).
    stride > 1 eğitimde komşu pencerelerin neredeyse aynı olması yüzünden seyreltme sağlar.
    """

    def __init__(self, df: pd.DataFrame, norm: prep.Normalizer, window=599,
                 period_s=config.SAMPLE_PERIOD_S, stride=1):
        if window % 2 == 0:
            raise ValueError("window tek sayı olmalı (hedef pencerenin ortasında)")
        self.window, self.norm = window, norm
        agg, app, starts, offset = [], [], [], 0
        for _, g in df.groupby(["house", "appliance"], sort=True):
            g = g.sort_values("timestamp")
            a = norm.x(g["aggregate_w"].to_numpy())
            t = norm.y(g["appliance_w"].to_numpy())
            for idx in prep._segments(g["timestamp"].reset_index(drop=True), period_s):
                n = len(idx)
                if n >= window:
                    starts.append(offset + np.arange(0, n - window + 1, stride))
                agg.append(a[idx])
                app.append(t[idx])
                offset += n
        self.agg = torch.from_numpy(np.concatenate(agg)) if agg else torch.empty(0)
        self.app = torch.from_numpy(np.concatenate(app)) if app else torch.empty(0)
        self.starts = np.concatenate(starts) if starts else np.empty(0, dtype=np.int64)

    def __len__(self):
        return len(self.starts)

    def __getitem__(self, i):
        s = int(self.starts[i])
        return self.agg[s:s + self.window], self.app[s + self.window // 2]


def load_processed(appliance: str, processed_dir=PROCESSED) -> pd.DataFrame:
    """data/processed/{cihaz}.h5 dosyasını okur (scripts.prepare_ukdale çıktısı)."""
    path = Path(processed_dir) / f"{appliance.replace(' ', '_')}.h5"
    if not path.exists():
        raise FileNotFoundError(f"{path} yok; işlenmiş veriyi data/processed/ içine koy ya da "
                                "python -m scripts.prepare_ukdale çalıştır")
    return prep.validate(pd.read_hdf(path, "data"))


def make_datasets(appliance: str, window=599, stride=1, val_stride=None, processed_dir=PROCESSED):
    """(train, val, test, norm): config'teki ev ayrımına göre; norm yalnızca eğitimden öğrenilir.

    test = config.UNSEEN_HOUSES (hiç görülmeyen ev). Cihaz bir evde yoksa o ev atlanır.
    val/test için stride varsayılan olarak `val_stride` (None ise 1: tüm pencereler).
    """
    df = load_processed(appliance, processed_dir)
    train_df, val_df, test_df = prep.split_by_house(
        df, config.TRAIN_HOUSES, config.VAL_HOUSES, config.UNSEEN_HOUSES)
    if train_df.empty:
        raise ValueError(f"{appliance}: eğitim evlerinde veri yok")
    norm = prep.Normalizer().fit(train_df)
    vs = val_stride or 1
    return (WindowDataset(train_df, norm, window, stride=stride),
            WindowDataset(val_df, norm, window, stride=vs),
            WindowDataset(test_df, norm, window, stride=vs),
            norm)
