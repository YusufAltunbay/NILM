"""PyTorch modelleri için ortak yardımcılar: seed, cihaz, erken durdurma, pencere kesme."""
import copy
import random

import numpy as np
import torch


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class EarlyStopping:
    """Doğrulama kaybı `patience` epoch iyileşmezse durur; en iyi ağırlıkları saklar."""

    def __init__(self, patience: int = 5):
        self.patience, self.best, self.bad, self.state = patience, float("inf"), 0, None

    def step(self, loss: float, net: torch.nn.Module) -> bool:
        """True dönerse eğitim durmalı."""
        if loss < self.best:
            self.best, self.bad = loss, 0
            self.state = copy.deepcopy(net.state_dict())
        else:
            self.bad += 1
        return self.bad >= self.patience

    def restore(self, net: torch.nn.Module) -> None:
        if self.state is not None:
            net.load_state_dict(self.state)


def gather_windows(agg: torch.Tensor, app: torch.Tensor, starts: torch.Tensor, idx: torch.Tensor,
                   window: int, ar: torch.Tensor):
    """Pencere başlangıçlarından toplu (x, y) keser. Hepsi aynı cihazda (GPU'da hızlı).

    agg/app: 1B normalleştirilmiş sinyaller, starts: pencere başlangıçları (WindowDataset.starts),
    idx: starts içinden seçilen sıra numaraları, ar: arange(window).
    """
    s = starts[idx]
    return agg[s[:, None] + ar[None, :]], app[s + window // 2]
