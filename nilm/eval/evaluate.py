import time
from nilm import config
from nilm.eval import metrics, results


def evaluate(model, test, dataset, appliance, log=True):
    agg, y = test["aggregate_w"].to_numpy(), test["appliance_w"].to_numpy()
    t0 = time.perf_counter()
    p = model.predict(agg)
    ms = (time.perf_counter() - t0) * 1000
    row = dict(model=model.name, dataset=dataset, appliance=appliance,
               mae=metrics.mae(y, p), sae=metrics.sae(y, p), f1=metrics.f1_on_off(y, p),
               tl_error=metrics.tl_error(y, p, config.SAMPLE_PERIOD_S, config.TL_PER_KWH),
               predict_ms=ms)
    if log:
        results.append(row)
    return row
