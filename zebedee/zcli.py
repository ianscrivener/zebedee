#!/usr/bin/env python3
"""Zebedee — an agent-native work ledger (v0.1).

All writes to the records store go through this script, via `just` (which runs it with `uv run`).
Stdlib only, apart from DuckDB for `index` (installed by `uv sync`).

Records location (first match wins):
  1. $Z_RECORDS
  2. records_path in z.toml (relative to the project root, or absolute)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # older Pythons: z.toml is simple enough to parse here
    tomllib = None
from pathlib import Path

STAGES = {
    -2: "idea", -1: "spike", 0: "decision", 1: "intent", 2: "spec",
    3: "unit-test", 4: "implementation", 5: "test-suite", 6: "observed",
}
TYPES = ["feature", "bug", "enhancement", "refactor", "chore"]
STATUSES = ["active", "parked", "rejected", "done"]
DOC_KINDS = ["spike", "decision", "spec"]
RUN_KINDS = ["unit", "suite", "bench"]
RUN_MODES = ["controlled", "observed"]

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"


# ---------------------------------------------------------------- helpers

def die(msg: str, code: int = 1) -> None:
    print(f"zebedee: error: {msg}", file=sys.stderr)
    sys.exit(code)


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_ts(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s)


def uuid7() -> str:
    if hasattr(uuid, "uuid7"):  # Python 3.14+
        return str(uuid.uuid7())
    ms = int(time.time() * 1000)
    b = bytearray(ms.to_bytes(6, "big") + os.urandom(10))
    b[6] = (b[6] & 0x0F) | 0x70  # version 7
    b[8] = (b[8] & 0x3F) | 0x80  # RFC 4122 variant
    return str(uuid.UUID(bytes=bytes(b)))


def as_of(value: str | None, floor: str | None = None) -> str | None:
    """Validate a historical timestamp (--as-of). Naive times are taken as local time."""
    if not value:
        return None
    try:
        d = dt.datetime.fromisoformat(value)
    except ValueError:
        die(f"--as-of must be ISO 8601, e.g. 2026-03-02 or 2026-03-02T14:30 (got '{value}')")
    if d.tzinfo is None:
        d = d.astimezone()
    if d > dt.datetime.now().astimezone():
        die("--as-of cannot be in the future")
    if floor and d < parse_ts(floor):
        die(f"--as-of {value} is before the item was created ({floor})")
    return d.isoformat(timespec="seconds")


def slugify(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:maxlen].rstrip("-") or "item"


# ---------------------------------------------------------------- config

def load_toml(path: Path) -> dict:
    if tomllib:
        with open(path, "rb") as f:
            return tomllib.load(f)
    cfg: dict = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.split(" #")[0].strip().replace("'", '"')
        try:
            cfg[k.strip()] = json.loads(v)
        except json.JSONDecodeError:
            die(f"z.toml: can't parse '{line}' — upgrade to Python 3.11+ for full TOML")
    return cfg


class Ctx:
    def __init__(self) -> None:
        self.root = self._find_root()
        self.cfg = load_toml(self.root / "z.toml")
        env = os.environ.get("Z_RECORDS")
        rp = Path(env) if env else Path(self.cfg.get("records_path", ".records"))
        self.records = (rp if rp.is_absolute() else self.root / rp).resolve()
        self.domains = [d.lower() for d in self.cfg.get("domains", [])]
        self.extra_types = [t.lower() for t in self.cfg.get("extra_types", [])]
        self.claim_timeout_h = float(self.cfg.get("claim_timeout_hours", 4))

    @staticmethod
    def _find_root() -> Path:
        p = Path.cwd().resolve()
        for d in [p, *p.parents]:
            if (d / "z.toml").exists():
                return d
        die("no z.toml found in this directory or any parent")

    # paths
    @property
    def work(self) -> Path: return self.records / "work"
    @property
    def agents(self) -> Path: return self.records / "agents"
    @property
    def events(self) -> Path: return self.records / "events"
    @property
    def runs(self) -> Path: return self.records / "results" / "runs"

    def require_records(self) -> None:
        if not self.work.is_dir():
            die(f"records store not found at {self.records} — run `just z-init`, "
                "or set Z_RECORDS to the mounted path")

    @property
    def types(self) -> list[str]:
        return TYPES + self.extra_types


# ---------------------------------------------------------------- frontmatter
# Format: '---' / 'key: value' lines / '---' / body.
# Values are JSON when they parse as JSON (numbers, null, lists), else plain strings.

def read_md(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    if not text.startswith("---\n"):
        return {}, text
    head, _, body = text[4:].partition("\n---\n")
    meta: dict = {}
    for line in head.splitlines():
        if not line.strip() or ":" not in line:
            continue
        k, _, v = line.partition(":")
        v = v.strip()
        try:
            meta[k.strip()] = json.loads(v)
        except json.JSONDecodeError:
            meta[k.strip()] = v
    return meta, body


def write_md(path: Path, meta: dict, body: str) -> None:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, str) and "\n" not in v and v.strip() == v and v:
            try:
                json.loads(v)          # would be mis-read as JSON → quote it
                lines.append(f"{k}: {json.dumps(v)}")
            except json.JSONDecodeError:
                lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {json.dumps(v)}")
    lines.append("---")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n" + body)
    tmp.replace(path)                  # atomic on the same filesystem


def render(template: str, **vals) -> str:
    text = (TEMPLATES / template).read_text()
    for k, v in vals.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


# ---------------------------------------------------------------- agents & events

def agent_file(ctx: Ctx, aid: str) -> Path:
    return ctx.agents / f"{aid}.json"


def require_agent(ctx: Ctx, aid: str | None) -> dict:
    if not aid:
        die("--agent <uuid> is required (run /z-ai-init to register)")
    f = agent_file(ctx, aid)
    if not f.exists():
        die(f"unknown agent {aid} — run /z-ai-init, or `just z-ai-whoami --session <id>` to recover")
    return json.loads(f.read_text())


def log_event(ctx: Ctx, aid: str, action: str, item: str | None = None,
              ts: str | None = None, **detail) -> None:
    # One events file per agent session → no concurrent writers on the same file.
    # ts = when it happened (historical if --as-of); recorded_at = when it was written.
    ev = {"ts": ts or now(), "recorded_at": now(), "agent": aid, "action": action, "item": item}
    if ts:
        ev["migrated"] = True
    ev.update(detail)
    with open(ctx.events / f"{aid}.jsonl", "a") as f:
        f.write(json.dumps(ev) + "\n")


def last_activity(ctx: Ctx, aid: str) -> str | None:
    f = ctx.events / f"{aid}.jsonl"
    if not f.exists():
        return None
    lines = f.read_text().strip().splitlines()
    if not lines:
        return None
    last = json.loads(lines[-1])
    return last.get("recorded_at") or last["ts"]   # activity = when written, not historical ts


def is_stale(ts: str | None, hours: float) -> bool:
    if not ts:
        return True
    age = dt.datetime.now().astimezone() - parse_ts(ts)
    return age.total_seconds() > hours * 3600


# ---------------------------------------------------------------- items

def item_dir(ctx: Ctx, iid: str) -> Path:
    d = ctx.work / iid
    if not (d / "item.md").exists():
        matches = [p for p in ctx.work.iterdir() if p.name.startswith(iid)] if ctx.work.exists() else []
        if len(matches) == 1:
            return matches[0]
        die(f"no item '{iid}'" + (f" (ambiguous: {len(matches)} matches)" if matches else ""))
    return d


def load_item(ctx: Ctx, iid: str) -> tuple[Path, dict, str]:
    d = item_dir(ctx, iid)
    meta, body = read_md(d / "item.md")
    return d, meta, body


def save_item(d: Path, meta: dict, body: str) -> None:
    meta["updated"] = now()
    write_md(d / "item.md", meta, body)


def claim_is_live(ctx: Ctx, meta: dict) -> bool:
    owner = meta.get("owner")
    if not owner:
        return False
    # A claim stays live while its owner has been active within the timeout.
    return not is_stale(last_activity(ctx, owner) or meta.get("claimed_at"), ctx.claim_timeout_h)


def require_owner(ctx: Ctx, meta: dict, aid: str) -> None:
    if meta.get("owner") != aid:
        die(f"item {meta['id']} is not claimed by you (owner: {meta.get('owner')}) — "
            "run `just z-item claim` first")


def all_items(ctx: Ctx) -> list[dict]:
    out = []
    if ctx.work.exists():
        for d in sorted(ctx.work.iterdir()):
            if (d / "item.md").exists():
                meta, _ = read_md(d / "item.md")
                meta["docs"] = sorted(p.stem for p in d.glob("*.md") if p.name != "item.md")
                out.append(meta)
    return out


# ---------------------------------------------------------------- commands

ZEBEDEE_README_TITLE = "# Zebedee — an agent-native work ledger"
SEED_MARKER = ".zebedee-seed"   # git-ignored; exists only in the Zebedee maintainer checkout
SEED_FILES = ["LICENSE", "CHANGELOG.md", "Zebedde-Decision-Register.md", "RETROFIT_PROMPT.md"]


def adopt_seed(ctx: Ctx) -> None:
    """Greenfield adoption: make the root the project's own.

    - README.md is copied to README-zebedee.md (the Zebedee manual); README.md stays for the project to rewrite.
    - Zebedee's own files (SEED_FILES) move into zebedee/.
    Acts only on a fresh clone of the seed (README.md is still the Zebedee README), never in the
    maintainer checkout (SEED_MARKER present), and never overwrites anything.
    """
    root = ctx.root
    if (root / SEED_MARKER).exists():
        print(f"seed checkout ({SEED_MARKER} present): leaving seed files in place")
        return
    readme = root / "README.md"
    if not (readme.exists() and readme.read_text().lstrip().startswith(ZEBEDEE_README_TITLE)):
        return                                   # retrofit or already adopted: the root is the project's
    manual = root / "README-zebedee.md"
    if not manual.exists():
        shutil.copyfile(readme, manual)
        print("copied README.md → README-zebedee.md (the Zebedee manual); README.md is now yours to rewrite")
    for name in SEED_FILES:
        src, dst = root / name, root / "zebedee" / name
        if src.exists() and not dst.exists():
            src.replace(dst)
            print(f"moved {name} → zebedee/{name}")


def cmd_setup(ctx: Ctx, a) -> None:
    adopt_seed(ctx)
    for d in (ctx.work, ctx.agents, ctx.events, ctx.runs):
        d.mkdir(parents=True, exist_ok=True)
    gi = ctx.records / ".gitignore"
    if not gi.exists():
        gi.write_text("# generated — never committed\nSTATUS.md\nindex.json\nindex.duckdb\n*.tmp\n")
    if shutil.which("git") and not (ctx.records / ".git").exists():
        subprocess.run(["git", "init", "-q", str(ctx.records)], check=True)
        print(f"initialised records git repo at {ctx.records}")
    outer = ctx.root / ".gitignore"
    rel = os.path.relpath(ctx.records, ctx.root)
    if not rel.startswith(".."):
        entry = f"/{rel}/"
        lines = outer.read_text().splitlines() if outer.exists() else []
        if entry not in lines:
            with open(outer, "a") as f:
                f.write(("\n" if lines and lines[-1] else "") + entry + "\n")
            print(f"added {entry} to {outer}")
    print(f"records store ready: {ctx.records}")


def cmd_init(ctx: Ctx, a) -> None:
    ctx.require_records()
    aid = uuid7()
    rec = {
        "uuid": aid, "harness": a.harness, "family": a.family, "model": a.model,
        "self_reported": True, "harness_session": a.session,
        "host": platform.node(), "os": platform.platform(), "registered_at": now(),
    }
    agent_file(ctx, aid).write_text(json.dumps(rec, indent=2) + "\n")
    log_event(ctx, aid, "register", harness=a.harness, model=a.model)
    print(aid)


def cmd_whoami(ctx: Ctx, a) -> None:
    ctx.require_records()
    hits = [json.loads(f.read_text()) for f in ctx.agents.glob("*.json")]
    hits = [h for h in hits if h.get("harness_session") == a.session]
    if not hits:
        die(f"no agent registered with harness session '{a.session}'")
    for h in sorted(hits, key=lambda h: h["registered_at"]):
        print(f"{h['uuid']}  {h['harness']} | {h['family']} | {h['model']}  ({h['registered_at']})")


def cmd_agents(ctx: Ctx, a) -> None:
    ctx.require_records()
    for f in sorted(ctx.agents.glob("*.json")):
        h = json.loads(f.read_text())
        print(f"{h['uuid']}  {h['registered_at']}  {h['harness']} | {h['family']} | {h['model']}")


def cmd_sessions(ctx: Ctx, a) -> None:
    ctx.require_records()
    claims: dict[str, list[str]] = {}
    for it in all_items(ctx):
        if it.get("owner"):
            claims.setdefault(it["owner"], []).append(it["id"])
    rows = []
    for f in sorted(ctx.agents.glob("*.json")):
        h = json.loads(f.read_text())
        last = last_activity(ctx, h["uuid"])
        state = "stale" if is_stale(last, ctx.claim_timeout_h) else "active"
        if a.active and state != "active":
            continue
        rows.append((state, h, last, claims.get(h["uuid"], [])))
    if not rows:
        print("no sessions")
    for state, h, last, held in rows:
        held_s = f"  holds: {', '.join(held)}" if held else ""
        print(f"[{state:6}] {h['uuid']}  {h['harness']} | {h['model']}  last: {last}{held_s}")


def cmd_item_new(ctx: Ctx, a) -> None:
    ctx.require_records()
    require_agent(ctx, a.agent)
    if a.type not in ctx.types:
        die(f"unknown type '{a.type}' — one of: {', '.join(ctx.types)}")
    domains = [d.strip().lower() for d in a.domains.split(",") if d.strip()]
    if not domains:
        die("at least one domain is required")
    bad = [d for d in domains if d not in ctx.domains]
    if bad:
        die(f"unknown domain(s) {bad} — this project declares: {', '.join(ctx.domains)}")
    if a.stage not in STAGES:
        die(f"stage must be one of {sorted(STAGES)}")
    if a.stage >= 1 and not a.intent:
        die("items entering at stage 1 or later need --intent")

    hist = as_of(a.as_of)
    when = parse_ts(hist) if hist else dt.datetime.now()
    base = when.strftime("%Y%m%d-%H%M") + "-" + slugify(a.title)
    iid, n = base, 2
    while True:
        try:
            (ctx.work / iid).mkdir()   # atomic: the directory is the reservation
            break
        except FileExistsError:
            iid, n = f"{base}-{n}", n + 1
    ts = now()
    meta = {
        "id": iid, "title": a.title, "type": a.type, "domains": domains,
        "entry_stage": a.stage, "stage": a.stage, "status": "active",
        "owner": a.agent, "claimed_at": ts,
        "created": hist or ts, "created_by": a.agent, "updated": ts,
        "revisit": None,
    }
    if hist:
        meta["migrated"] = True
    body = render("item.md", intent=a.intent or "_Not yet stated._")
    write_md(ctx.work / iid / "item.md", meta, body)
    log_event(ctx, a.agent, "item.new", iid, ts=hist, stage=a.stage, type=a.type)
    print(iid)


def cmd_item_list(ctx: Ctx, a) -> None:
    ctx.require_records()
    items = all_items(ctx)
    if a.stage is not None:
        items = [i for i in items if i["stage"] == a.stage]
    if a.type:
        items = [i for i in items if i["type"] == a.type]
    if a.domain:
        items = [i for i in items if a.domain.lower() in i["domains"]]
    if a.status:
        items = [i for i in items if i["status"] == a.status]
    elif not a.all:
        items = [i for i in items if i["status"] == "active"]
    if a.owner:
        items = [i for i in items if i.get("owner") == a.owner]
    if a.json:
        print(json.dumps(items, indent=2))
        return
    if not items:
        print("no items")
    for i in items:
        own = " *claimed*" if i.get("owner") else ""
        print(f"{i['stage']:>2} {STAGES[i['stage']]:<14} {i['status']:<8} {i['type']:<11} "
              f"{i['id']}  [{','.join(i['domains'])}]{own}")


def cmd_item_show(ctx: Ctx, a) -> None:
    ctx.require_records()
    d, meta, body = load_item(ctx, a.id)
    print((d / "item.md").read_text())
    docs = sorted(p.name for p in d.glob("*.md") if p.name != "item.md")
    if docs:
        print("docs: " + ", ".join(str(d / x) for x in docs))


def cmd_item_claim(ctx: Ctx, a) -> None:
    ctx.require_records()
    require_agent(ctx, a.agent)
    d, meta, body = load_item(ctx, a.id)
    owner = meta.get("owner")
    if owner and owner != a.agent and claim_is_live(ctx, meta) and not a.force:
        die(f"item is claimed by {owner} (active) — use --force only if that session is dead")
    meta["owner"], meta["claimed_at"] = a.agent, now()
    save_item(d, meta, body)
    log_event(ctx, a.agent, "item.claim", meta["id"], previous_owner=owner, forced=bool(a.force))
    print(f"claimed {meta['id']}")


def cmd_item_release(ctx: Ctx, a) -> None:
    ctx.require_records()
    require_agent(ctx, a.agent)
    d, meta, body = load_item(ctx, a.id)
    owner = meta.get("owner")
    if owner != a.agent and not a.force:
        die(f"item is owned by {owner}, not you — use --force to release a dead session's claim")
    meta["owner"], meta["claimed_at"] = None, None
    save_item(d, meta, body)
    log_event(ctx, a.agent, "item.release", meta["id"], previous_owner=owner, forced=bool(a.force))
    print(f"released {meta['id']}")


def cmd_item_stage(ctx: Ctx, a) -> None:
    ctx.require_records()
    require_agent(ctx, a.agent)
    d, meta, body = load_item(ctx, a.id)
    require_owner(ctx, meta, a.agent)
    cur, to = meta["stage"], a.to
    if to not in STAGES:
        die(f"stage must be one of {sorted(STAGES)}")
    if meta["status"] != "active":
        die(f"item is {meta['status']}; only active items move")
    if cur == 0 and to > 0:
        die("leaving stage 0 requires a decision — use `just z-item decide`")
    if to == cur:
        die("item is already at that stage")
    if to > cur + 1:
        die(f"forward moves are one step at a time ({cur} → {cur + 1})")
    if to < cur and not a.reason:
        die("backward moves need --reason")
    hist = as_of(a.as_of, meta["created"])
    meta["stage"] = to
    save_item(d, meta, body)
    log_event(ctx, a.agent, "item.stage", meta["id"], ts=hist, frm=cur, to=to, reason=a.reason)
    print(f"{meta['id']}: {cur} ({STAGES[cur]}) → {to} ({STAGES[to]})")


def cmd_item_decide(ctx: Ctx, a) -> None:
    ctx.require_records()
    require_agent(ctx, a.agent)
    d, meta, body = load_item(ctx, a.id)
    require_owner(ctx, meta, a.agent)
    if meta["stage"] != 0:
        die(f"decisions happen at stage 0 (item is at {meta['stage']}) — advance it first")
    if a.verdict == "park" and not a.revisit:
        die("parking needs --revisit '<trigger>'")
    hist = as_of(a.as_of, meta["created"])
    (d / "decision.md").write_text(render(
        "decision.md", id=meta["id"], verdict=a.verdict, reason=a.reason,
        revisit=a.revisit or "—", date=hist or now(), agent=a.agent))
    if a.verdict == "commit":
        meta["stage"] = 1
    elif a.verdict == "reject":
        meta["status"], meta["owner"], meta["claimed_at"] = "rejected", None, None
    else:
        meta["status"], meta["revisit"] = "parked", a.revisit
        meta["owner"], meta["claimed_at"] = None, None
    save_item(d, meta, body)
    log_event(ctx, a.agent, "item.decide", meta["id"], ts=hist, verdict=a.verdict, reason=a.reason)
    print(f"{meta['id']}: {a.verdict}")


def cmd_item_reopen(ctx: Ctx, a) -> None:
    ctx.require_records()
    require_agent(ctx, a.agent)
    d, meta, body = load_item(ctx, a.id)
    if meta["status"] != "parked":
        die(f"only parked items reopen (item is {meta['status']})")
    hist = as_of(a.as_of, meta["created"])
    meta["status"], meta["revisit"] = "active", None
    meta["owner"], meta["claimed_at"] = a.agent, now()
    save_item(d, meta, body)
    log_event(ctx, a.agent, "item.reopen", meta["id"], ts=hist, reason=a.reason)
    print(f"{meta['id']}: reopened at stage {meta['stage']} — decide again when ready")


def cmd_item_close(ctx: Ctx, a) -> None:
    ctx.require_records()
    require_agent(ctx, a.agent)
    d, meta, body = load_item(ctx, a.id)
    require_owner(ctx, meta, a.agent)
    if meta["stage"] < 5:
        die("items are closed from stage 5 (test suite) or 6 (observed)")
    hist = as_of(a.as_of, meta["created"])
    meta["status"], meta["owner"], meta["claimed_at"] = "done", None, None
    save_item(d, meta, body)
    log_event(ctx, a.agent, "item.close", meta["id"], ts=hist)
    print(f"{meta['id']}: done")


def cmd_item_doc(ctx: Ctx, a) -> None:
    ctx.require_records()
    require_agent(ctx, a.agent)
    d, meta, body = load_item(ctx, a.id)
    require_owner(ctx, meta, a.agent)
    if a.kind == "decision":
        die("decision.md is written by `just z-item decide`")
    path = d / f"{a.kind}.md"
    if path.exists():
        print(path)
        return
    path.write_text(render(f"{a.kind}.md", id=meta["id"], title=meta["title"], date=now(), agent=a.agent))
    log_event(ctx, a.agent, "item.doc", meta["id"], kind=a.kind)
    print(path)


def _run(cmd: list[str], cwd: Path | None = None) -> str | None:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def env_snapshot() -> dict:
    """Best effort. Inside a Linux container this describes the VM, not the Mac host."""
    snap = {
        "platform": platform.platform(), "machine": platform.machine(),
        "python": platform.python_version(), "cpus": os.cpu_count(),
        "in_container": Path("/.dockerenv").exists() or Path("/run/.containerenv").exists(),
    }
    if sys.platform == "darwin":
        snap["swap"] = _run(["sysctl", "-n", "vm.swapusage"])
        snap["memory_pressure"] = _run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"])
        snap["thermal"] = _run(["pmset", "-g", "therm"])
        snap["power"] = _run(["pmset", "-g", "batt"])
        snap["macos"] = _run(["sw_vers", "-productVersion"])
    elif Path("/proc/meminfo").exists():
        mi = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, _, v = line.partition(":")
            if k in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
                mi[k] = v.strip()
        snap["meminfo"] = mi
        try:
            snap["loadavg"] = os.getloadavg()
        except OSError:
            pass
    return snap


def cmd_run_record(ctx: Ctx, a) -> None:
    ctx.require_records()
    require_agent(ctx, a.agent)
    if a.item:
        item_dir(ctx, a.item)  # validates
    metrics_src = a.metrics
    if metrics_src.startswith("@"):
        metrics_src = Path(metrics_src[1:]).read_text()
    try:
        metrics = json.loads(metrics_src)
    except json.JSONDecodeError as e:
        die(f"--metrics must be JSON (or @file): {e}")
    sha = _run(["git", "rev-parse", "HEAD"], cwd=ctx.root)
    dirty = bool(_run(["git", "status", "--porcelain"], cwd=ctx.root))
    hist = as_of(a.as_of)
    rid = uuid7()
    rec = {
        "run_id": rid, "ts": hist or now(), "recorded_at": now(), "agent": a.agent, "item": a.item,
        "kind": a.kind, "mode": a.mode, "name": a.name, "passed": a.passed,
        "git_sha": sha, "git_dirty": dirty, "harness_version": a.harness_version,
        "metrics": metrics, "env": env_snapshot(),
    }
    if hist:
        # Migrated run: git SHA and env describe the moment of import, not the original run.
        rec["migrated"] = True
        rec["git_sha"], rec["git_dirty"] = a.git_sha, None
        rec["env"] = {"captured": "at import, not at original run", **rec["env"]}
    stamp = (parse_ts(hist) if hist else dt.datetime.now()).strftime("%Y%m%d-%H%M%S")
    path = ctx.runs / f"{stamp}-{rid[-8:]}.jsonl"   # one file per run → no merge conflicts
    path.write_text(json.dumps(rec) + "\n")
    log_event(ctx, a.agent, "run.record", a.item, ts=hist, run_id=rid, kind=a.kind)
    print(rid)


def load_runs(ctx: Ctx) -> list[dict]:
    runs = []
    for f in sorted(ctx.runs.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                runs.append(json.loads(line))
    return runs


def cmd_run_list(ctx: Ctx, a) -> None:
    ctx.require_records()
    runs = load_runs(ctx)
    if a.item:
        runs = [r for r in runs if r["item"] and r["item"].startswith(a.item)]
    if a.name:
        runs = [r for r in runs if r["name"] == a.name]
    if a.kind:
        runs = [r for r in runs if r["kind"] == a.kind]
    runs = runs[-a.limit:]
    if a.json:
        print(json.dumps(runs, indent=2))
        return
    for r in runs:
        res = {True: "pass", False: "FAIL", None: "-"}[r["passed"]]
        print(f"{r['ts']}  {r['kind']:<5} {r['mode']:<10} {res:<4} {r['name']:<24} "
              f"{(r['git_sha'] or '-')[:8]}{'+' if r['git_dirty'] else ''}  {json.dumps(r['metrics'])}")


def cmd_status(ctx: Ctx, a) -> None:
    ctx.require_records()
    items = all_items(ctx)
    active = [i for i in items if i["status"] == "active"]
    out = [f"# Status — {ctx.root.name}", f"_Generated {now()}. Do not edit._", ""]
    out.append("## Active items by stage")
    for s, name in STAGES.items():
        here = [i for i in active if i["stage"] == s]
        if here:
            out.append(f"- **{s} {name}** ({len(here)}): " + ", ".join(i["id"] for i in here))
    if not active:
        out.append("- none")
    parked = [i for i in items if i["status"] == "parked"]
    if parked:
        out += ["", "## Parked"] + [f"- {i['id']} — revisit: {i.get('revisit')}" for i in parked]
    stale = [i for i in active if i.get("owner") and not claim_is_live(ctx, i)]
    if stale:
        out += ["", "## Stale claims"] + [f"- {i['id']} (owner {i['owner']})" for i in stale]
    runs = load_runs(ctx)[-5:]
    if runs:
        out += ["", "## Latest runs"]
        for r in runs:
            res = {True: "pass", False: "FAIL", None: "-"}[r["passed"]]
            out.append(f"- {r['ts']} {r['kind']} `{r['name']}` {res} {json.dumps(r['metrics'])}")
    text = "\n".join(out) + "\n"
    if a.write:
        (ctx.records / "STATUS.md").write_text(text)
    print(text, end="")


def cmd_index(ctx: Ctx, a) -> None:
    ctx.require_records()
    items = all_items(ctx)
    (ctx.records / "index.json").write_text(json.dumps(items, indent=2) + "\n")
    print(f"wrote {ctx.records / 'index.json'} ({len(items)} items)")
    try:
        import duckdb  # optional
    except ImportError:
        print("duckdb not installed — skipped index.duckdb (install it in the project env: `uv add duckdb` or `pip install duckdb`)")
        return
    db = ctx.records / "index.duckdb"
    db.unlink(missing_ok=True)
    con = duckdb.connect(str(db))
    con.execute(f"CREATE TABLE items AS SELECT * FROM read_json_auto('{ctx.records / 'index.json'}')")
    if any(ctx.runs.glob("*.jsonl")):
        con.execute(f"CREATE TABLE runs AS SELECT * FROM read_json_auto('{ctx.runs}/*.jsonl')")
    if any(ctx.events.glob("*.jsonl")):
        con.execute(f"CREATE TABLE events AS SELECT * FROM read_json_auto('{ctx.events}/*.jsonl')")
    con.close()
    print(f"wrote {db}")


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="zebedee", description="Zebedee — an agent-native work ledger")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("setup", help="create the records store")

    s = sub.add_parser("init", help="register an agent session; prints its UUID")
    s.add_argument("--harness", required=True)
    s.add_argument("--family", required=True)
    s.add_argument("--model", required=True)
    s.add_argument("--session", help="harness session ID, if known")

    s = sub.add_parser("whoami", help="recover your UUID from your harness session ID")
    s.add_argument("--session", required=True)

    sub.add_parser("agents", help="list all registered agent sessions (the manifest)")

    s = sub.add_parser("sessions", help="list sessions as active / stale, with claims held")
    s.add_argument("--active", action="store_true", help="active only")

    it = sub.add_parser("item", help="work items").add_subparsers(dest="sub", required=True)

    s = it.add_parser("new")
    s.add_argument("--agent", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--type", required=True)
    s.add_argument("--domains", required=True, help="comma-separated")
    s.add_argument("--stage", type=int, default=-2, help="entry stage (default -2, idea)")
    s.add_argument("--intent", help="1-2 sentences; required when entering at stage ≥1")
    s.add_argument("--as-of", help="historical timestamp (ISO 8601) — for migrating past work")

    s = it.add_parser("list")
    s.add_argument("--stage", type=int)
    s.add_argument("--type")
    s.add_argument("--domain")
    s.add_argument("--status", choices=STATUSES)
    s.add_argument("--owner")
    s.add_argument("--all", action="store_true", help="include parked/rejected/done")
    s.add_argument("--json", action="store_true")

    s = it.add_parser("show")
    s.add_argument("id")

    for name in ("claim", "release"):
        s = it.add_parser(name)
        s.add_argument("id")
        s.add_argument("--agent", required=True)
        s.add_argument("--force", action="store_true")

    s = it.add_parser("stage")
    s.add_argument("id")
    s.add_argument("--agent", required=True)
    s.add_argument("--to", type=int, required=True)
    s.add_argument("--reason")
    s.add_argument("--as-of", help="historical timestamp (ISO 8601) — for migrating past work")

    s = it.add_parser("decide")
    s.add_argument("id")
    s.add_argument("--agent", required=True)
    s.add_argument("--verdict", required=True, choices=["commit", "reject", "park"])
    s.add_argument("--reason", required=True)
    s.add_argument("--revisit", help="trigger for revisiting (required for park)")
    s.add_argument("--as-of", help="historical timestamp (ISO 8601) — for migrating past work")

    s = it.add_parser("reopen", help="un-park an item (back to stage 0, claimed by you)")
    s.add_argument("id")
    s.add_argument("--agent", required=True)
    s.add_argument("--reason", required=True, help="e.g. the revisit trigger fired")
    s.add_argument("--as-of", help="historical timestamp (ISO 8601) — for migrating past work")

    s = it.add_parser("close")
    s.add_argument("id")
    s.add_argument("--agent", required=True)
    s.add_argument("--as-of", help="historical timestamp (ISO 8601) — for migrating past work")

    s = it.add_parser("doc", help="create spike.md or spec.md from template; prints path")
    s.add_argument("id")
    s.add_argument("kind", choices=DOC_KINDS)
    s.add_argument("--agent", required=True)

    rn = sub.add_parser("run", help="test and benchmark results").add_subparsers(dest="sub", required=True)
    s = rn.add_parser("record")
    s.add_argument("--agent", required=True)
    s.add_argument("--kind", required=True, choices=RUN_KINDS)
    s.add_argument("--mode", default="controlled", choices=RUN_MODES)
    s.add_argument("--name", required=True, help="test/benchmark name")
    s.add_argument("--metrics", required=True, help="JSON object, or @path/to/file.json")
    s.add_argument("--item", help="related work item id")
    s.add_argument("--harness-version", required=True)
    s.add_argument("--as-of", help="historical timestamp (ISO 8601) — for migrating past work")
    s.add_argument("--git-sha", help="with --as-of: the commit the original run was made at")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--pass", dest="passed", action="store_true", default=None)
    g.add_argument("--fail", dest="passed", action="store_false")

    s = rn.add_parser("list")
    s.add_argument("--item")
    s.add_argument("--name")
    s.add_argument("--kind", choices=RUN_KINDS)
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("status", help="generated summary")
    s.add_argument("--write", action="store_true", help="also write STATUS.md in the records store")

    sub.add_parser("index", help="build index.json (and index.duckdb if duckdb is installed)")
    return p


DISPATCH = {
    ("setup", None): cmd_setup, ("init", None): cmd_init, ("whoami", None): cmd_whoami,
    ("agents", None): cmd_agents, ("sessions", None): cmd_sessions,
    ("item", "new"): cmd_item_new, ("item", "list"): cmd_item_list, ("item", "show"): cmd_item_show,
    ("item", "claim"): cmd_item_claim, ("item", "release"): cmd_item_release,
    ("item", "stage"): cmd_item_stage, ("item", "decide"): cmd_item_decide,
    ("item", "close"): cmd_item_close, ("item", "reopen"): cmd_item_reopen, ("item", "doc"): cmd_item_doc,
    ("run", "record"): cmd_run_record, ("run", "list"): cmd_run_list,
    ("status", None): cmd_status, ("index", None): cmd_index,
}


def main(argv: list[str] | None = None) -> None:
    a = build_parser().parse_args(argv)
    DISPATCH[(a.cmd, getattr(a, "sub", None))](Ctx(), a)


if __name__ == "__main__":
    main()
