"""Cihaz bazlı model ayarları: (model, cihaz) -> yapıcı argümanları. Boşsa modelin varsayılanı geçerlidir.

Her satır, ev 5 (doğrulama) üzerinde 3 seed ile doğrulanmış bir denemeye dayanır; kayıtlar
results/experiments.csv'de ("s2p-h256" notlu satırlar). Ev 2 hakem olarak kaldı.
"""

PARAMS: dict[tuple[str, str], dict] = {
    # Küçük Dense başlık: yanlış alarmı azaltıyor. Ev 5 MAE'si 3 seed'de de hidden=1024'ten düşük.
    ("seq2point", "microwave"): {"hidden": 256},
    ("seq2point", "dish washer"): {"hidden": 256},
}


def params(model: str, appliance: str) -> dict:
    """Modelin bu cihaz için yapıcı argümanları (kopya; çağıran değiştirebilir)."""
    return dict(PARAMS.get((model, appliance), {}))
