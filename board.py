#!/usr/bin/env python3
"""Structured, leased research board. No market data enters prompts.

Artifacts are exact strategy.py bytes addressed by SHA-256. Events are JSONL:
propose, claim, release, screened, audited, verdict. Claims expire after 45 min.
"""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

AGENT = re.compile(r"^v19n-[0-9]+$")
KINDS = {"reproduce", "causality", "robustness", "finalist"}
LEASE = timedelta(minutes=45)
FIELDS = ("family", "symbols", "mechanism", "hypothesis", "falsification")


def now():
    return datetime.now(timezone.utc)


def event(kind, agent, **fields):
    return {"id": uuid.uuid4().hex, "ts": now().isoformat(), "kind": kind,
            "agent": agent, **fields}


def append(root, record):
    path = root / "events.jsonl"
    with path.open("a") as out:
        fcntl.flock(out, fcntl.LOCK_EX)
        out.write(json.dumps(record, allow_nan=False) + "\n")
        out.flush()
        os.fsync(out.fileno())


def load(root):
    rows = []
    with (root / "events.jsonl").open() as source:
        for line in source:
            if line.strip():
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
    return rows


def state(root):
    artifacts, tasks = {}, {}
    for row in load(root):
        kind, agent = row.get("kind"), row.get("agent")
        if kind == "propose":
            sha = row["sha256"]
            artifacts[sha] = {**row, "screen": None, "audits": {}, "verdict": None}
        elif kind == "screened" and row["sha256"] in artifacts:
            artifacts[row["sha256"]]["screen"] = row
        elif kind == "audited" and row["sha256"] in artifacts:
            artifacts[row["sha256"]]["audits"][row["audit"]] = row
        elif kind == "verdict" and row["sha256"] in artifacts:
            artifacts[row["sha256"]]["verdict"] = row
        if "task_id" not in row:
            continue
        task_id = row["task_id"]
        if kind == "claim":
            tasks[task_id] = {**row, "released": False}
        elif kind in ("release", "audited") and task_id in tasks and tasks[task_id]["agent"] == agent:
            tasks[task_id]["released"] = True
    for sha, artifact in artifacts.items():
        artifact["open_tasks"] = [t for t in tasks.values() if t["sha256"] == sha and not t["released"]]
    return artifacts


class locked:
    def __init__(self, root): self.root = root
    def __enter__(self):
        self.file = (self.root / "board.lock").open("a+")
        fcntl.flock(self.file, fcntl.LOCK_EX)
        return self.file
    def __exit__(self, *args):
        self.file.close()


def validate_agent(agent):
    if not AGENT.fullmatch(agent):
        raise ValueError("invalid provisioned agent name")


def text(value, limit, name):
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise ValueError(f"invalid {name}")
    return value


def propose(root, agent, args):
    validate_agent(agent)
    source = args.strategy.read_bytes()
    if not source or len(source) > 128 * 1024:
        raise ValueError("strategy must be 1..131072 bytes")
    sha = hashlib.sha256(source).hexdigest()
    if sha in state(root):
        raise ValueError("artifact already proposed")
    target = root / "artifacts" / f"{sha}.py"
    if target.exists() and target.read_bytes() != source:
        raise RuntimeError("SHA collision")
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
            tmp.write(source)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.link(tmp.name, target)
        os.unlink(tmp.name)
        target.chmod(0o444)
    if not args.symbols or any(not s.isalnum() for s in args.symbols):
        raise ValueError("invalid symbols")
    record = event("propose", agent, sha256=sha, family=text(args.family, 80, "family"),
                   symbols=args.symbols, mechanism=text(args.mechanism, 500, "mechanism"),
                   hypothesis=text(args.hypothesis, 500, "hypothesis"),
                   falsification=text(args.falsification, 500, "falsification"))
    append(root, record)
    print(json.dumps({"sha256": sha, "artifact": str(target)}))


def claim(root, agent, args):
    validate_agent(agent)
    artifacts = state(root)
    artifact = artifacts.get(args.sha256)
    if artifact is None:
        raise ValueError("unknown artifact")
    if artifact["agent"] == agent:
        raise ValueError("author cannot independently review own artifact")
    if artifact["verdict"] is not None:
        raise ValueError("artifact already has final verdict")
    live = [t for t in artifact["open_tasks"]
            if now() - datetime.fromisoformat(t["ts"]) < LEASE]
    if any(t["audit"] == args.audit for t in live):
        raise ValueError("audit already leased")
    screen = artifact["screen"]
    if not screen:
        raise ValueError("screen required before independent review")
    causal = screen.get("causal_pass") is True
    positive = screen.get("primary", 0) > 0
    economic = screen.get("economic_pass") is True
    if not (causal and positive and economic):
        raise ValueError("artifact has not passed causal/economic/positive-primary screen")
    if args.audit in artifact["audits"]:
        raise ValueError("audit already completed")
    if args.audit == "finalist" and not {"causality", "reproduce", "robustness"} <= set(artifact["audits"]):
        raise ValueError("independent reproduction, causality and robustness required")
    if args.audit == "finalist" and agent in {r["agent"] for r in artifact["audits"].values()}:
        raise ValueError("finalist audit needs a fresh independent reviewer")
    if args.audit == "finalist" and not all(artifact["audits"][k].get("passed") for k in ("causality", "reproduce", "robustness")):
        raise ValueError("all prerequisite audits must pass")
    task_id = hashlib.sha256(f"{args.sha256}:{args.audit}".encode()).hexdigest()[:20]
    record = event("claim", agent, task_id=task_id, sha256=args.sha256, audit=args.audit)
    append(root, record)
    print(json.dumps(record))


def screen(root, agent, args):
    validate_agent(agent)
    artifact = state(root).get(args.sha256)
    if artifact is None or artifact["agent"] != agent:
        raise ValueError("only artifact author may attach screening evidence")
    record = event("screened", agent, sha256=args.sha256,
                   causal_pass=args.causal_pass, economic_pass=args.economic_pass,
                   primary=args.primary, evidence=text(args.evidence, 1000, "evidence"))
    append(root, record)
    print(json.dumps(record))


def audit(root, agent, args):
    validate_agent(agent)
    task = next((t for t in state(root).get(args.sha256, {}).get("open_tasks", [])
                 if t["task_id"] == args.task_id and t["agent"] == agent and not t["released"]), None)
    if task is None:
        raise ValueError("no matching live claim")
    if now() - datetime.fromisoformat(task["ts"]) >= LEASE:
        raise ValueError("claim expired; reclaim before auditing")
    record = event("audited", agent, task_id=args.task_id, sha256=args.sha256,
                   audit=task["audit"], passed=args.passed,
                   reproduction_exact=args.reproduction_exact,
                   evidence=text(args.evidence, 2000, "evidence"))
    append(root, record)
    print(json.dumps(record))


def verdict(root, agent, args):
    validate_agent(agent)
    if not agent.endswith("-10"):
        raise ValueError("only coordinator queen may finalize board verdict")
    artifact = state(root).get(args.sha256)
    if not artifact or not artifact["audits"].get("finalist", {}).get("passed"):
        raise ValueError("passed finalist audit required")
    record = event("verdict", agent, sha256=args.sha256, nominated=args.nominated,
                   evidence=text(args.evidence, 1000, "evidence"))
    append(root, record)
    print(json.dumps(record))


def summary(root):
    rows = []
    for artifact in state(root).values():
        screen = artifact["screen"] or {}
        rows.append({"sha256": artifact["sha256"], "author": artifact["agent"],
                     "family": artifact["family"], "symbols": artifact["symbols"],
                     "primary": screen.get("primary"), "screen_ready": bool(
                         screen.get("causal_pass") and screen.get("economic_pass") and screen.get("primary", 0) > 0),
                     "audits": sorted(artifact["audits"]),
                     "open_tasks": [{"task_id": t["task_id"], "audit": t["audit"], "agent": t["agent"]}
                                    for t in artifact["open_tasks"]
                                    if now() - datetime.fromisoformat(t["ts"]) < LEASE],
                     "verdict": artifact["verdict"]})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/board"))
    parser.add_argument("--agent", required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("propose"); p.add_argument("--strategy", type=Path, default=Path("strategy.py"))
    p.add_argument("--family", required=True); p.add_argument("--symbols", nargs="+", required=True)
    p.add_argument("--mechanism", required=True); p.add_argument("--hypothesis", required=True)
    p.add_argument("--falsification", required=True)
    for name in KINDS:
        p = sub.add_parser("claim-" + name); p.add_argument("sha256")
    p = sub.add_parser("release"); p.add_argument("task_id"); p.add_argument("sha256")
    p = sub.add_parser("screen"); p.add_argument("sha256"); p.add_argument("--causal-pass", action="store_true")
    p.add_argument("--economic-pass", action="store_true"); p.add_argument("--primary", type=float, required=True)
    p.add_argument("--evidence", required=True)
    p = sub.add_parser("audit"); p.add_argument("task_id"); p.add_argument("sha256")
    p.add_argument("--passed", action="store_true"); p.add_argument("--reproduction-exact", action="store_true")
    p.add_argument("--evidence", required=True)
    p = sub.add_parser("verdict"); p.add_argument("sha256"); p.add_argument("--nominated", action="store_true")
    p.add_argument("--evidence", required=True)
    p = sub.add_parser("list"); p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("show"); p.add_argument("sha256")
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    (args.root / "artifacts").mkdir(exist_ok=True)
    if not (args.root / "events.jsonl").exists():
        (args.root / "events.jsonl").touch()
    if args.action == "propose":
        with locked(args.root): propose(args.root, args.agent, args)
    elif args.action.startswith("claim-"):
        args.audit = args.action[6:]
        with locked(args.root): claim(args.root, args.agent, args)
    elif args.action == "release":
        validate_agent(args.agent)
        with locked(args.root):
            tasks = [t for a in state(args.root).values() for t in a["open_tasks"]]
            task = next((t for t in tasks if t["task_id"] == args.task_id and t["sha256"] == args.sha256), None)
            if not task or task["agent"] != args.agent: raise ValueError("claim not owned by caller")
            append(args.root, event("release", args.agent, task_id=args.task_id, sha256=args.sha256))
    elif args.action == "screen":
        with locked(args.root): screen(args.root, args.agent, args)
    elif args.action == "audit":
        with locked(args.root): audit(args.root, args.agent, args)
    elif args.action == "verdict":
        with locked(args.root): verdict(args.root, args.agent, args)
    elif args.action == "show":
        row = next((x for x in summary(args.root) if x["sha256"] == args.sha256), None)
        if row is None: raise ValueError("unknown artifact")
        print(json.dumps(row, indent=2))
    else:
        if not 1 <= args.limit <= 100: raise ValueError("limit must be 1..100")
        print(json.dumps(summary(args.root)[-args.limit:], indent=2))


if __name__ == "__main__":
    main()
