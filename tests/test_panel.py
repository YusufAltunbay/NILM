import pandas as pd
from panel import theme


def _bill(real, pred):
    idx = ["fridge", "kettle"]
    return pd.DataFrame({"Gerçek (TL)": real, "Tahmin (TL)": pred}, index=idx)


def test_summary_over_prediction():
    s = theme.summary_sentence(_bill([100.0, 50.0], [110.0, 70.0]))
    assert "%" in s and "fazla" in s
    assert "Su ısıtıcısı" in s          # en büyük sapma (+20 TL)
    assert "Buzdolabı" in s             # en yakın tahmin (%10 sapma)


def test_summary_under_prediction():
    s = theme.summary_sentence(_bill([100.0, 50.0], [90.0, 40.0]))
    assert "eksik" in s


def test_summary_exact():
    s = theme.summary_sentence(_bill([100.0, 50.0], [100.0, 50.0]))
    assert "neredeyse tam" in s


def test_tr_and_color_known_and_unknown():
    assert theme.tr("fridge") == "Buzdolabı"
    assert theme.tr("toaster") == "Toaster"
    assert theme.color("toaster").startswith("#")


def test_ordered_keeps_unknown_appliances():
    from panel import theme
    assert theme.ordered(["tv", "kettle", "fridge"]) == ["fridge", "kettle", "tv"]
    assert theme.color("tv") == theme.color("tv")  # çalıştırmalar arasında kararlı
