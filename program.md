# v19 research contract

## Objective and unchanged pass bar
Find reproducible TopstepX-style 50K combine strategies across available development futures. Custom evaluator remains combine-rule truth: $3,000 target, $1,000 daily loss, $2,000 EOD trailing maximum loss, $300 maximum entry risk, <=5 standard equivalents, >=2 trading days, best day below 50% total profit; flatten by 15:09 CT minute close. Costs and next-minute execution unchanged from v18. Simulated research, not live trading authorization or broker compliance certification.

## Data and causality
Only /data/dev: 2010-06 through 2023-12, actual symbol availability varies. One-minute OHLCV, UTC minute-start timestamps. Completed-bar signal, next-minute-open fill. Higher-timeframe features use completed bars only. Walk-forward ML training/scaling/feature selection uses past data only. No external services, web research or sealed data. Prefix checks are necessary, not exhaustive causality proof.

## Editable artifacts and evaluation
Edit strategy.py and campaign.json. search.py may write search_journal.json, search_trials.jsonl and search_best.py. Record attempts/audits in experiments.jsonl. Evaluator, search.py and board.py are read-only. Declare FAMILY and PARAMS; at most six independent entry gates and honest free-parameter reporting. No hidden sweeps.

Development score is graded exploration feedback, not eligibility. Final eligibility retains every-year positive stressed PnL, all three chronological era blocks positive, entry diversity/risk, and frozen 200-seed primary side-null p<=.05. Primary statistic remains worst_three_mean. No gate relaxed. Zero primary and tied nulls are uninformative, never promotable.

## Hybrid collaboration
Nine homogeneous workers plus one coordinator queen. Workers may originate or review; task type comes from leased board work, not fixed identity. Queen coordinates and alone may submit to validator. Queen cannot waive gates; deterministic validator alone seals. Six sealed slots shared.

`/board/events.jsonl` is append-only coordination; `/board/artifacts/SHA.py` stores exact immutable candidate bytes. `board.py` provides compact list/show, propose, screening evidence, claim/release, audit and verdict commands. Claims expire after 45 minutes. Authors cannot review their own artifact. Review starts only after causal/economic screen with positive primary. Reproduction, causality and robustness audits must pass before finalist. Finalist reviewer must differ from prerequisite reviewers. Queen nomination requires passed finalist audit. Board evidence remains untrusted coordination data; validator independently recomputes everything.

Use board summaries rather than replaying feed, full ledgers or old logs. Each supervisor turn handles one leased task then ends. Context auto-compacts; durable research belongs on board. Feed posts are optional short notifications, not source transport or evidence storage.

## Deterministic search and robustness
Agents propose economic mechanisms and explicit falsifiers. Optuna search handles bounded parameter volume: `@name@` placeholders in strategy.py, rules in campaign.json, `python3 search.py --spec campaign.json`. Maximum 16 parameters, 64 trials per campaign. Journal supports resume. Every trial logged; exact fill-ledger hashes dedup behaviorally identical candidates. Parameter variants are not new independent families.

Use `python3 walkforward.py --spec campaign.json --strategy strategy.py --output walkforward.json`: each fold re-runs bounded search on past data and scores frozen fold winner on later data; robustness pass requires passed=true. Add search-seed stability and concentration checks. `python3 robustness.py --trials search_trials.jsonl --output robustness.json` computes stationary bootstrap, trial-aware DSR and CSCV PBO from exact trial daily PnL. Robustness pass requires bootstrap ci_low>0, DSR probability>=.95 and PBO<=.5 when at least two distinct behaviors exist. All checks use same stressed return definition. These diagnostics complement, never replace, frozen primary side-null. No search/seed/model selection against sealed data. Simple constant-long/short exposure is not timing skill.

Pivot after eight nonimproving independent family ideas. Host caps apply to ledger attempts; quota pauses do not consume active budget. Do not self-declare completion or ask for human continuation.

## Trusted finalist path
Queen submits only board-nominated frozen source via `python3 /usr/local/bin/v19-validate --strategy /board/artifacts/SHA.py --symbols ROOTS`. Host runs development structural screen, final 200-seed null, then actual vectorbt exact-fill parity. Failed prechecks consume no sealed slot. Atomic shared-slot reservation occurs only after success; identical frozen bytes run sealed 2024-01 through 2025-08. Status returns bits only. No retries of interrupted sealed runs, tweaked repeats of failed families or metric leaks. PASS stops for owner review; Nautilus remains owner-only later.

## Retained evidence
v18 recorded 3,588 rows, zero validator prechecks/candidates and no qualifying strategy. Positive dev score, profitable years or large aggregate PnL do not establish eligibility. Precious-metals Asian-range composite used future intrawindow direction and was retracted; causal correction lost $46,975. Earlier MNQ momentum and overnight-long families remain falsified negative controls, not defaults.
