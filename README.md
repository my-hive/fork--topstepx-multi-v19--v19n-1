# TopstepX multi-asset v19

Hybrid research swarm: nine homogeneous workers, one coordinator queen, dynamic independent review, bounded Optuna search, behavioral dedup, dev-only robustness diagnostics, and deterministic sealed validation.

## Baseline

```bash
bash eval/eval.sh --data /data/dev --symbols MES MGC --strategy strategy.py \
  --output report.json --null-seeds 0 --mode dev
python3 test_board.py
python3 test_search.py
python3 test_robustness.py
```

Read `program.md` for editable artifacts, board protocol, gates and trust boundaries. `/board` is shared coordination only; it never grants validation authority.

## Owner readiness

No v19 task, identities or research processes are created by this package. Owner preparation publishes and provisions; launch remains blocked until `OWNER_READINESS_APPROVED` exists after sandbox/security/smoke review.
