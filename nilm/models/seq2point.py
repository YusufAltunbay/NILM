"""seq2point (Zhang vd., AAAI 2018): 599 adımlık toplam güç penceresi -> ortadaki cihaz gücü.

Mimari: 5 x Conv1D (30/30/40/50/50 filtre, çekirdek 10/8/6/5/5) -> Dense(1024) -> Dense(1).
Veri: nilm.data.dataset.WindowDataset (pencere __getitem__ yerine GPU'da toplu kesilir).
Çıkarım: nilm.models.windowed.WindowedModel (kenar dolgusu, kırpma, aynı uzunluk).
"""
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from nilm import config
from nilm.data.dataset import WindowDataset
from nilm.models.torch_utils import EarlyStopping, gather_windows, get_device, seed_everything
from nilm.models.windowed import WindowedModel

CKPT_DIR = Path(__file__).resolve().parents[2] / "models_ckpt"  # *.pt git dışı


class Seq2PointNet(nn.Module):
    def __init__(self, window=599, dropout=0.2, hidden=1024, center=False):
        super().__init__()
        self.center = center  # her pencereden kendi medyanını çıkar (taban yük farkına dayanıklılık)
        chans, kernels, layers, c_in = [30, 30, 40, 50, 50], [10, 8, 6, 5, 5], [], 1
        for c, k in zip(chans, kernels):
            layers += [nn.Conv1d(c_in, c, k, padding="same"), nn.ReLU()]
            c_in = c
        self.conv = nn.Sequential(*layers)
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(c_in * window, hidden), nn.ReLU(),
                                  nn.Dropout(dropout), nn.Linear(hidden, 1))

    def forward(self, x):  # x: (B, window)
        if self.center:
            x = x - x.median(dim=1, keepdim=True).values
        return self.head(self.conv(x.unsqueeze(1))).squeeze(-1)


class Seq2Point(WindowedModel):
    name = "seq2point"

    def __init__(self, window=599, stride=20, lr=1e-3, train_batch=256, dropout=0.2,
                 hidden=1024, weight_decay=0.0, center=False, on_frac=0.5, epochs=30, patience=5, seed=0, verbose=True):
        """stride: eğitim pencerelerinin seyreltilmesi (hız). on_frac: batch'lerdeki AÇIK pencere
        oranı (None = doğal dağılım). Doğrulama kaybı patience epoch iyileşmezse durur."""
        self.window, self.stride, self.lr, self.train_batch = window, stride, lr, train_batch
        self.dropout, self.on_frac, self.epochs = dropout, on_frac, epochs
        self.hidden, self.weight_decay, self.center = hidden, weight_decay, center
        self.patience, self.seed, self.verbose = patience, seed, verbose
        self.device = get_device()
        self.amp = self.device.type == "cuda"  # karma hassasiyet: ~%35 daha hızlı
        self.net: Seq2PointNet | None = None
        self.history: list[dict] = []

    # -- eğitim ---------------------------------------------------------------------------
    def fit(self, train, val=None):
        seed_everything(self.seed)
        app = train["appliance"].iloc[0]
        norm = self.fit_normalizer(train)
        tr = WindowDataset(train, norm, self.window, stride=self.stride)
        if len(tr) == 0:
            raise ValueError(f"{app}: eğitimde {self.window} adımlık pencere yok")
        dev, w = self.device, self.window
        agg, y_all, starts = tr.agg.to(dev), tr.app.to(dev), torch.from_numpy(tr.starts).to(dev)
        if val is not None and len(val):
            va = WindowDataset(val, norm, self.window, stride=5)
            v_agg, v_app, v_starts = va.agg.to(dev), va.app.to(dev), torch.from_numpy(va.starts).to(dev)
        else:  # doğrulama evi yok: eğitim pencerelerinin her 10 bloğundan biri (500'lük) ayrılır
            blk = (torch.arange(len(starts), device=dev) // 500) % 10 == 9
            v_agg, v_app, v_starts = agg, y_all, starts[blk]
            starts = starts[~blk]
        if len(v_starts) == 0:
            raise ValueError(f"{app}: doğrulama penceresi yok")

        ar = torch.arange(w, device=dev)
        thr = config.ON_THRESHOLD_W.get(app, config.DEFAULT_ON_THRESHOLD_W) / norm.app_max
        is_on = y_all[starts + w // 2] > thr
        n_on = int(is_on.sum())
        weights = None
        if self.on_frac and 0 < n_on < len(starts):
            weights = torch.where(is_on, self.on_frac / n_on, (1 - self.on_frac) / (len(starts) - n_on))

        self.net = Seq2PointNet(w, self.dropout, self.hidden, self.center).to(dev)
        opt = torch.optim.AdamW(self.net.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        scaler = torch.amp.GradScaler(enabled=self.amp)
        stopper, loss_fn, n = EarlyStopping(self.patience), nn.MSELoss(), len(starts)
        steps = (n + self.train_batch - 1) // self.train_batch
        for ep in range(1, self.epochs + 1):
            t0 = time.perf_counter()
            self.net.train()
            order = (torch.multinomial(weights, n, replacement=True) if weights is not None
                     else torch.randperm(n, device=dev))
            tot = 0.0
            for i in range(0, n, self.train_batch):
                x, y = gather_windows(agg, y_all, starts, order[i:i + self.train_batch], w, ar)
                with torch.autocast(dev.type, dtype=torch.float16, enabled=self.amp):
                    loss = loss_fn(self.net(x).float(), y)
                opt.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(opt)
                scaler.update()
                tot += loss.item() * len(x)
                k = i // self.train_batch + 1
                if self.verbose and k % max(1, steps // 4) == 0 and k < steps:
                    print(f"[{app}]   epoch {ep:02d} %{100 * k // steps} "
                          f"(loss {tot / (i + len(x)):.5f})", flush=True)
            v_loss = self._val_loss(v_agg, v_app, v_starts, ar)
            self.history.append(dict(epoch=ep, train_loss=tot / n, val_loss=v_loss,
                                     sec=time.perf_counter() - t0))
            if self.verbose:
                print(f"[{app}] epoch {ep:02d} train {tot / n:.5f} val {v_loss:.5f} "
                      f"({self.history[-1]['sec']:.0f} sn)", flush=True)
            if stopper.step(v_loss, self.net):
                break
        stopper.restore(self.net)
        self.net.eval()
        self.appliance_ = app
        return self

    @torch.no_grad()
    def _val_loss(self, agg, app, starts, ar, batch=2048) -> float:
        self.net.eval()
        tot = 0.0
        for i in range(0, len(starts), batch):
            idx = torch.arange(i, min(i + batch, len(starts)), device=agg.device)
            x, y = gather_windows(agg, app, starts, idx, self.window, ar)
            with torch.autocast(self.device.type, dtype=torch.float16, enabled=self.amp):
                out = self.net(x).float()
            tot += ((out - y) ** 2).sum().item()
        return tot / len(starts)

    # -- çıkarım --------------------------------------------------------------------------
    @torch.no_grad()
    def predict_batch(self, x: np.ndarray) -> np.ndarray:
        self.net.eval()
        with torch.autocast(self.device.type, dtype=torch.float16, enabled=self.amp):
            out = self.net(torch.from_numpy(x).to(self.device))
        return out.float().cpu().numpy()

    # -- ağırlıklar -----------------------------------------------------------------------
    def save(self, path: Path | None = None) -> Path:
        path = Path(path or CKPT_DIR / f"{self.name}__{self.appliance_.replace(' ', '_')}.pt")
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"state": self.net.state_dict(), "norm": vars(self.norm), "window": self.window,
                    "dropout": self.dropout, "hidden": self.hidden, "center": self.center, "seed": self.seed, "history": self.history}, path)
        return path
