import argparse
from pathlib import Path
import tempfile

import board


def args(**kw):
    return argparse.Namespace(**kw)


def check():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "board"
        (root / "artifacts").mkdir(parents=True)
        (root / "events.jsonl").touch()
        strategy = Path(tmp) / "strategy.py"
        strategy.write_text("FAMILY='test'\n")
        proposal = args(strategy=strategy, family="test", symbols=["MES"], mechanism="m",
                        hypothesis="h", falsification="f")
        board.propose(root, "v19n-1", proposal)
        sha = board.state(root).keys().__iter__().__next__()
        assert (root / "artifacts" / (sha + ".py")).read_bytes() == strategy.read_bytes()
        for actor in ("v19n-1", "v19n-2"):
            try:
                board.claim(root, actor, args(sha256=sha, audit="reproduce"))
            except ValueError:
                pass
            else:
                raise AssertionError("claim bypassed self-review/screen")
        board.screen(root, "v19n-1", args(sha256=sha, causal_pass=True, economic_pass=True,
                                          primary=.01, evidence="report sha"))
        for kind, actor in (("reproduce", "v19n-2"), ("causality", "v19n-3"), ("robustness", "v19n-4")):
            board.claim(root, actor, args(sha256=sha, audit=kind))
            task = board.state(root)[sha]["open_tasks"][0]
            board.audit(root, actor, args(sha256=sha, task_id=task["task_id"], passed=True,
                                         reproduction_exact=True, evidence="independent evidence"))
        try:
            board.claim(root, "v19n-2", args(sha256=sha, audit="finalist"))
        except ValueError:
            pass
        else:
            raise AssertionError("same reviewer reached final audit")
        board.claim(root, "v19n-5", args(sha256=sha, audit="finalist"))
        task = board.state(root)[sha]["open_tasks"][0]
        board.audit(root, "v19n-5", args(sha256=sha, task_id=task["task_id"], passed=True,
                                        reproduction_exact=True, evidence="final audit"))
        board.verdict(root, "v19n-10", args(sha256=sha, nominated=True, evidence="nominated"))
        assert board.summary(root)[0]["verdict"]["nominated"] is True
        try:
            board.claim(root, "v19n-6", args(sha256=sha, audit="reproduce"))
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate review allowed")
    print("v19 board self-check ok: exact source, screening, leases, independent audits, queen verdict")


if __name__ == "__main__":
    check()
