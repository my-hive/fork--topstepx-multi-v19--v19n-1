import json
import os
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

import search


def check():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "campaign.json"
        path.write_text('{"space":{"lookback":{"type":"int","low":5,"high":40}},"symbols":["MES"],"trials":4}')
        spec = search.load_spec(path)
        assert search.render("x=@lookback@", {"lookback": 10}) == "x=10"
        for bad in (
            '{"space":{},"symbols":["MES"]}',
            '{"space":{"x":{"type":"int","low":2,"high":1}},"symbols":["MES"]}',
            '{"space":{"x":{"type":"float","low":0,"high":1}},"symbols":["../../x"]}',
        ):
            path.write_text(bad)
            try:
                search.load_spec(path)
            except ValueError:
                pass
            else:
                raise AssertionError("accepted invalid campaign")
        try:
            search.render("x=1", {"lookback": 10})
        except ValueError:
            pass
        else:
            raise AssertionError("accepted unused search parameter")

        # Real two-trial Optuna + evaluator smoke on synthetic development-shaped bars.
        root = Path(tmp) / "smoke"
        data = root / "data"
        data.mkdir(parents=True)
        index = pd.date_range("2024-01-02 16:00", periods=8, freq="min", tz="UTC", name="ts")
        values = np.arange(100., 108.)
        ct = index.tz_convert("America/Chicago")
        pd.DataFrame({"open": values, "high": values+1, "low": values-1, "close": values,
                      "volume": 10, "contract": "MESH4", "session": "2024-01-02",
                      "ct_sec": ct.hour*3600+ct.minute*60}, index=index).to_parquet(data/"MES.parquet")
        (root / "eval").symlink_to(Path(__file__).resolve().parent / "eval", target_is_directory=True)
        (root / "strategy.py").write_text('''import numpy as np
FAMILY="search-smoke"
PARAMS={"side": 1}
def signals(panel):
    return {s: np.full(len(d), @side@, dtype=np.int64) for s,d in panel.items()}
def entry_risk(panel):
    return {s: np.full(len(d), 100.) for s,d in panel.items()}
''')
        (root / "campaign.json").write_text(json.dumps({"space": {"side": {"type": "categorical", "choices": [-1, 1]}},
            "symbols": ["MES"], "trials": 2, "data": str(data), "timeout_seconds": 60}))
        old = os.getcwd()
        os.chdir(root)
        try:
            search.run(Path("campaign.json"))
            rows = [json.loads(line) for line in Path("search_trials.jsonl").read_text().splitlines()]
            assert len(rows) == 2 and all(r["returncode"] == 0 for r in rows), rows
            assert Path("search_best.py").exists()
            assert all("daily_pnl" in r and "behavior_sha256" in r for r in rows)
        finally:
            os.chdir(old)
    print("v19 search self-check ok: bounded specs, real Optuna/eval, source/daily-PnL artifacts")


if __name__ == "__main__":
    check()
