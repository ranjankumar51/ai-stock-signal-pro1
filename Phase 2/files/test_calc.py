import numpy as np

from app.analysis.technical import calc


def test_sma():
    out = calc.sma(np.array([1.0, 2, 3, 4]), 2)
    assert np.isnan(out[0])
    assert np.allclose(out[1:], [1.5, 2.5, 3.5])


def test_ema_constant_is_constant():
    out = calc.ema(np.array([5.0, 5, 5, 5]), 3)
    assert np.allclose(out, 5.0)


def test_ema_seed_and_step():
    out = calc.ema(np.array([0.0, 10.0]), 2)  # alpha = 2/3
    assert out[0] == 0.0
    assert np.isclose(out[1], 10.0 * (2 / 3))


def test_rma_seed_is_sma():
    out = calc.rma(np.array([1.0, 1, 1, 1]), 2)
    assert np.isnan(out[0])
    assert np.allclose(out[1:], 1.0)


def test_true_range():
    h = np.array([10.0, 12, 11])
    lo = np.array([8.0, 9, 7])
    c = np.array([9.0, 11, 8])
    tr = calc.true_range(h, lo, c)
    assert tr[0] == 2.0  # 10-8
    # bar1: max(12-9, |12-9|, |9-9|) = 3
    assert tr[1] == 3.0


def test_rolling_std():
    out = calc.rolling_std(np.array([1.0, 2, 3, 4]), 2, ddof=0)
    assert np.isnan(out[0])
    assert np.allclose(out[1:], 0.5)
