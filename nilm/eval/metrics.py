import numpy as np


def mae(y, p):
    return float(np.mean(np.abs(y - p)))


def sae(y, p):
    return float(abs(p.sum() - y.sum()) / max(y.sum(), 1e-9))


def f1_on_off(y, p, threshold_w=15.0):
    yt, pt = y > threshold_w, p > threshold_w
    tp = np.sum(yt & pt); fp = np.sum(~yt & pt); fn = np.sum(yt & ~pt)
    return float(2 * tp / max(2 * tp + fp + fn, 1))


def tl_error(y, p, sample_period_s, tl_per_kwh):
    kwh = lambda x: x.sum() * sample_period_s / 3600 / 1000
    return float(abs(kwh(p) - kwh(y)) * tl_per_kwh)
