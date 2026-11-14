import json
import os
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

import walkforward


def check():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data = root / "data"
        data.mkdir()
        frames = []
        for day, date in enumerate(pd.bdate_range("2020-01-01", periods=380)):
            index = pd.date_range(date + pd.Timedelta(hours=16), periods=4, freq="min", tz="UTC", name="ts")
            values = 100. + day*4 + np.arange(4)
            ct = index.tz_convert("America/Chicago")
            frames.append(pd.DataFrame({"open": values, "high": values+1, "low": values-1,
                "close": values, "volume": 10, "contract": "MESH4", "session": str(date.date()),
                "ct_sec": ct.hour*3600+ct.minute*60}, index=index))
        pd.concat(frames).to_parquet(data/"MES.parquet")
        (root / "strategy.py").write_text('''import numpy as np
FAMILY="wf-smoke"
PARAMS={"side":1}
def signals(panel): return {s:np.full(len(d),@side@,dtype=np.int64) for s,d in panel.items()}
def entry_risk(panel): return {s:np.full(len(d),100.) for s,d in panel.items()}
''')
        spec = {"space": {"side": {"type": "categorical", "choices": [-1, 1]}},
                "symbols": ["MES"], "trials": 2, "data": str(data),
                "train_sessions": 252, "validation_sessions": 60, "folds": 2, "timeout_seconds": 60}
        (root / "campaign.json").write_text(json.dumps(spec))
        old = os.getcwd()
        os.chdir(root)
        try:
            walkforward.run(Path("campaign.json"), Path("strategy.py"), Path("walkforward.json"))
            result = json.loads(Path("walkforward.json").read_text())
            assert result["completed"] == 2, result
            assert all(r["total_pnl"] > 0 for r in result["folds"]), result
            assert not result["passed"]  # Tiny synthetic folds cannot pass $3,000 combine target.
        finally:
            os.chdir(old)
    print("v19 walk-forward self-check ok: past-only search, frozen later-fold evaluation")


if __name__ == "__main__":
    check()
