"""BERT4NILM (Yue vd., 2020): çift yönlü Transformer ile seq2seq NILM, küçük sürüm.

Seq2point her pencere için tek bir değer (ortadaki an) üretir. Burada ağ bir pencerenin TAMAMI için
cihaz gücünü birden verir; çıkarımda pencereler üst üste bindirilip çıktılar ortalanır, bu yüzden
seq2point'ten çok daha az ağ çağrısı gerekir.

Mimari: Conv1D giriş gömmesi + 2x alt örnekleme -> öğrenilmiş konum gömmesi -> Transformer encoder
(self-attention, çift yönlü) -> ConvTranspose1D ile üst örnekleme -> Linear(128)-tanh-Linear(1).
Seq2point ile AYNI: ev ayrımı, normalizasyon (Normalizer), pencere medyanı çıkarma (center), açık/kapalı
örnekleme (on_frac), doğrulama yedeği, kayıp (MSE), seed ve karma hassasiyet (adil karşılaştırma).
"""
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from nilm import config
from nilm.data.dataset import WindowDataset
from nilm.data.prep import Normalizer
from nilm.models.base import NILMModel
from nilm.models.torch_utils import EarlyStopping, get_device, seed_everything

CKPT_DIR = Path(__file__).resolve().parents[2] / "models_ckpt"  # *.pt git dışı


class Bert4NilmNet(nn.Module):
    def __init__(self, window=481, hidden=64, layers=2, heads=2, dropout=0.1, center=True):
        super().__init__()
        self.window, self.center = window, center
        self.embed = nn.Sequential(nn.Conv1d(1, hidden, 5, padding=2), nn.ReLU())
        self.pool = nn.MaxPool1d(2, 2, ceil_mode=True)  # L -> ceil(L/2) token
        self.n_tok = (window + 1) // 2
        self.pos = nn.Parameter(torch.randn(1, self.n_tok, hidden) * 0.02)
        layer = nn.TransformerEncoderLayer(hidden, heads, 4 * hidden, dropout, activation="gelu",
                                           batch_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.deconv = nn.ConvTranspose1d(hidden, hidden, 4, stride=2, padding=1)  # token -> 2 x token
        self.head = nn.Sequential(nn.Linear(hidden, 128), nn.Tanh(), nn.Linear(128, 1))

    def forward(self, x):  # x: (B, window) -> (B, window)
        if self.center:
            x = x - x.median(dim=1, keepdim=True).values
        h = self.pool(self.embed(x.unsqueeze(1)))  # (B, H, T)
        h = self.encoder(h.transpose(1, 2) + self.pos)  # (B, T, H)
        h = self.deconv(h.transpose(1, 2))[..., :self.window]  # (B, H, L)
        return self.head(h.transpose(1, 2)).squeeze(-1)


class Bert4Nilm(NILMModel):
    name = "bert4nilm"

    def __init__(self, window=481, hidden=64, layers=2, heads=2, dropout=0.1, lr=3e-4, train_batch=64,
                 on_frac=0.35, cover=2.0, hop=None, weight_decay=0.0, center=True, epochs=30,
                 patience=3, seed=0, verbose=True):
        """window tek sayı olmalı (WindowDataset kuralı). cover: bir epoch'ta her sinyal noktası ortalama
        kaç pencerede görülür (epoch büyüklüğü = cover x sinyal uzunluğu / window). on_frac: epoch'taki,
        içinde AÇIK nokta bulunan pencerelerin oranı. hop: çıkarımda pencere kaydırma (varsayılan window//4)."""
        self.window, self.hidden, self.layers, self.heads, self.dropout = window, hidden, layers, heads, dropout
        self.lr, self.train_batch, self.on_frac, self.cover = lr, train_batch, on_frac, cover
        self.hop, self.weight_decay, self.center = hop or max(1, window // 4), weight_decay, center
        self.epochs, self.patience, self.seed, self.verbose = epochs, patience, seed, verbose
        self.device = get_device()
        self.amp = self.device.type == "cuda"
        self.net: Bert4NilmNet | None = None
        self.norm: Normalizer | None = None
        self.history: list[dict] = []

    # -- eğitim ---------------------------------------------------------------------------
    def fit(self, train, val=None):
        seed_everything(self.seed)
        app = train["appliance"].iloc[0]
        self.norm = norm = Normalizer().fit(train)
        L, dev = self.window, self.device
        tr = WindowDataset(train, norm, L, stride=1)
        if len(tr) == 0:
            raise ValueError(f"{app}: eğitimde {L} adımlık pencere yok")
        agg, y_all, starts = tr.agg.to(dev), tr.app.to(dev), torch.from_numpy(tr.starts).to(dev)
        thr = config.ON_THRESHOLD_W.get(app, config.DEFAULT_ON_THRESHOLD_W) / norm.app_max
        ar = torch.arange(L, device=dev)

        use_val = val is not None and len(val) > 0
        if use_val:
            va = WindowDataset(val, norm, L, stride=L)  # çakışmayan doğrulama pencereleri
            v_agg, v_app, v_starts = va.agg.to(dev), va.app.to(dev), torch.from_numpy(va.starts).to(dev)
            on_ratio = float((v_app > thr).float().mean()) if len(v_app) else 0.0
            if on_ratio < 1e-3:  # doğrulama evinde cihaz neredeyse hiç açılmamış: kayıp anlamsız
                if self.verbose:
                    print(f"[{app}] doğrulama evinde açık oranı %{100 * on_ratio:.2f}: "
                          "erken durdurma için eğitim verisinden blok ayırılıyor", flush=True)
                use_val = False
        if not use_val:  # her 10 bloğun 1'i ayrılır, kenarlardan L pencere atılır
            pos = torch.arange(len(starts), device=dev)
            bs = max(2 * L, min(20_000, len(starts) // 20))
            blk, r = pos // bs, pos % bs
            is_val = blk % 10 == 9
            guard = ((blk % 10 == 8) & (r >= bs - L)) | ((blk % 10 == 0) & (blk > 0) & (r < L))
            v_agg, v_app, v_starts = agg, y_all, starts[is_val][::L]
            starts = starts[~is_val & ~guard]
        if len(v_starts) == 0 or len(starts) == 0:
            raise ValueError(f"{app}: eğitim/doğrulama penceresi yok")

        # pencere "açık": içinde en az bir AÇIK nokta var (kümülatif toplamla hızlı hesap)
        cs = torch.cat([torch.zeros(1, dtype=torch.int32, device=dev), torch.cumsum((y_all > thr).int(), 0, dtype=torch.int32)])
        win_on = (cs[starts + L] - cs[starts]) > 0
        on_idx, off_idx = torch.nonzero(win_on).squeeze(1), torch.nonzero(~win_on).squeeze(1)
        balanced = bool(self.on_frac) and len(on_idx) > 0 and len(off_idx) > 0
        n = max(self.train_batch, int(self.cover * len(agg) / L))

        def draw() -> torch.Tensor:
            if not balanced:
                return torch.randint(len(starts), (n,), device=dev)
            k_on = int(round(self.on_frac * n))
            idx = torch.cat([on_idx[torch.randint(len(on_idx), (k_on,), device=dev)],
                             off_idx[torch.randint(len(off_idx), (n - k_on,), device=dev)]])
            return idx[torch.randperm(len(idx), device=dev)]

        def batch(a, b, st, idx):
            s = st[idx][:, None] + ar[None, :]
            return a[s], b[s]

        self.net = Bert4NilmNet(L, self.hidden, self.layers, self.heads, self.dropout, self.center).to(dev)
        opt = torch.optim.AdamW(self.net.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        scaler = torch.amp.GradScaler(enabled=self.amp)
        stopper, loss_fn = EarlyStopping(self.patience), nn.MSELoss()
        steps = (n + self.train_batch - 1) // self.train_batch
        for ep in range(1, self.epochs + 1):
            t0 = time.perf_counter()
            self.net.train()
            order, tot = draw(), 0.0
            for i in range(0, n, self.train_batch):
                x, y = batch(agg, y_all, starts, order[i:i + self.train_batch])
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
    def _val_loss(self, agg, app, starts, ar, batch=256) -> float:
        self.net.eval()
        tot = 0.0
        for i in range(0, len(starts), batch):
            s = starts[i:i + batch][:, None] + ar[None, :]
            with torch.autocast(self.device.type, dtype=torch.float16, enabled=self.amp):
                out = self.net(agg[s]).float()
            tot += ((out - app[s]) ** 2).sum().item()
        return tot / (len(starts) * self.window)

    # -- çıkarım --------------------------------------------------------------------------
    @torch.no_grad()
    def predict(self, aggregate, batch=256):
        """Pencereleri hop adımıyla kaydırır, çakışan çıktıları ortalar; girişle aynı uzunlukta döner."""
        if self.net is None or self.norm is None:
            raise RuntimeError("önce fit() çağır")
        agg = np.asarray(aggregate, dtype="float64")
        n, L = len(agg), self.window
        if n == 0:
            return np.empty(0, dtype="float32")
        x = np.pad(self.norm.x(agg), (0, max(0, L - n)), mode="edge")  # kısa girişte sağdan doldur
        m = len(x)
        starts = np.unique(np.minimum(np.arange(0, m - L + self.hop, self.hop), m - L))
        acc, cnt = np.zeros(m, "float32"), np.zeros(m, "float32")
        self.net.eval()
        for i in range(0, len(starts), batch):
            s = starts[i:i + batch]
            xb = torch.from_numpy(np.stack([x[a:a + L] for a in s])).to(self.device)
            with torch.autocast(self.device.type, dtype=torch.float16, enabled=self.amp):
                out = self.net(xb).float().cpu().numpy()
            for a, o in zip(s, out):
                acc[a:a + L] += o
                cnt[a:a + L] += 1
        y = (acc / cnt)[:n]
        y = np.clip(self.norm.y_inverse(y), 0.0, None).astype("float32")
        return np.minimum(y, agg.astype("float32"))  # float32'de de toplamı aşmaz

    # -- ağırlıklar -----------------------------------------------------------------------
    def save(self, path: Path | None = None) -> Path:
        path = Path(path or CKPT_DIR / f"{self.name}__{self.appliance_.replace(' ', '_')}.pt")
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"state": self.net.state_dict(), "norm": vars(self.norm), "window": self.window,
                    "hidden": self.hidden, "layers": self.layers, "heads": self.heads,
                    "dropout": self.dropout, "center": self.center, "seed": self.seed,
                    "history": self.history}, path)
        return path
