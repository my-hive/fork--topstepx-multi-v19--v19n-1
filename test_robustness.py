import numpy as np

import robustness


def check():
    rng = np.random.default_rng(19)
    values = rng.normal(10, 100, 200)
    result = robustness.bootstrap(values, samples=20)
    assert result["samples"] == 20
    assert robustness.dsr(values, 1, [10])["probability"] > .5
    try:
        robustness.sharpe(np.zeros(200))
    except ValueError:
        pass
    else:
        raise AssertionError("constant exposure/PnL accepted")
    matrix = np.tile(np.arange(160)[:, None] % 3 - 1, (1, 2))
    assert robustness.pbo(matrix)["partitions"] == 12870
    print("v19 robustness self-check ok: bootstrap, trial-aware DSR, CSCV, constant-series rejection")


if __name__ == "__main__":
    check()
