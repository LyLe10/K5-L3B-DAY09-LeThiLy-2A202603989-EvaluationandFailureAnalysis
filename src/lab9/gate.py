"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from numbers import Real
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    from lab9.graders import GRADERS

    problems: list[str] = []
    graded = {m.get("id") for m in spec.get("metrics", [])
              if isinstance(m, dict) and m.get("id") in GRADERS}
    pair_maps = {}
    for name, report in (("pr", pr), ("baseline", base)):
        if not isinstance(report, dict):
            problems.append(f"{name}: report is not an object")
            continue
        manifest, rows, metrics = report.get("manifest"), report.get("rows"), report.get("metrics")
        if not isinstance(manifest, dict) or not isinstance(rows, list) or not isinstance(metrics, dict):
            problems.append(f"{name}: malformed manifest, rows or metrics")
            continue
        failures = report.get("evaluator_failures")
        if not isinstance(failures, list) or failures:
            problems.append(f"{name}: evaluator failures or missing failure list")
        for metric, value in metrics.items():
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                problems.append(f"{name}: invalid aggregate metric {metric}")
        items, seeds = manifest.get("items"), manifest.get("seeds")
        valid_manifest = (type(items) is int and items > 0 and isinstance(seeds, list) and bool(seeds)
                          and all(type(seed) is int for seed in seeds) and len(set(seeds)) == len(seeds))
        if not valid_manifest:
            problems.append(f"{name}: invalid manifest item count or seeds")
            continue
        if len(rows) != items * len(seeds):
            problems.append(f"{name}: row count does not match manifest")
        if "seeds" in spec and seeds != spec["seeds"]:
            problems.append(f"{name}: seeds differ from spec")
        pairs = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("item_id"), str) or type(row.get("seed")) is not int:
                problems.append(f"{name}: malformed row identity")
                continue
            pair = (row["item_id"], row["seed"])
            if pair in pairs:
                problems.append(f"{name}: duplicate item/seed pair")
            tags = row.get("slices", [])
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                problems.append(f"{name}: malformed slice tags")
                continue
            pairs[pair] = frozenset(tags)
            for metric in graded:
                value = row.get(metric)
                if not isinstance(value, Real) or not math.isfinite(value):
                    problems.append(f"{name}: invalid row metric {metric}")
        item_ids = {pair[0] for pair in pairs}
        if len(item_ids) != items or set(pairs) != {(item, seed) for item in item_ids for seed in seeds}:
            problems.append(f"{name}: incomplete item/seed coverage")
        pair_maps[name] = pairs
    if "pr" in pair_maps and "baseline" in pair_maps:
        a, b = pair_maps["pr"], pair_maps["baseline"]
        if set(a) != set(b):
            problems.append("pr: item/seed pairs differ from baseline")
        if any(a[pair] != b[pair] for pair in set(a) & set(b)):
            problems.append("pr: slice tags differ from baseline")
    if base_spec is not None:
        current_version = spec.get("eval_set_version")
        base_version = base_spec.get("eval_set_version") if isinstance(base_spec, dict) else None
        if not current_version or not base_version:
            problems.append("ratchet: missing eval_set_version")
        elif current_version == base_version:
            def index_rules(rules, kind):
                result = {}
                if not isinstance(rules, list):
                    problems.append(f"ratchet: malformed {kind} rules")
                    return result
                for rule in rules:
                    if not isinstance(rule, dict):
                        problems.append(f"ratchet: malformed {kind} rule")
                        continue
                    identity = rule.get("id") if kind == "metric" else (rule.get("name"), rule.get("metric"))
                    if ((kind == "metric" and not isinstance(identity, str)) or
                        (kind == "slice" and not all(isinstance(part, str) and part for part in identity))):
                        problems.append(f"ratchet: invalid {kind} identity")
                        continue
                    if identity in result:
                        problems.append(f"ratchet: duplicate {kind} {identity}")
                    result[identity] = rule
                return result

            for kind, key in (("metric", "metrics"), ("slice", "slices")):
                original = index_rules(base_spec.get(key, []), kind)
                current = index_rules(spec.get(key, []), kind)
                for identity, before in original.items():
                    after = current.get(identity)
                    if after is None:
                        problems.append(f"ratchet: removed {kind} {identity}")
                        continue
                    if before.get("blocking") is True and after.get("blocking") is not True:
                        problems.append(f"ratchet: {kind} {identity} no longer blocking")
                    old_threshold = before.get("threshold", {}) if kind == "metric" else before
                    new_threshold = after.get("threshold", {}) if kind == "metric" else after
                    if not isinstance(old_threshold, dict) or not isinstance(new_threshold, dict):
                        problems.append(f"ratchet: malformed threshold for {kind} {identity}")
                        continue
                    for field in ("min", "max", "max_increase"):
                        if field not in old_threshold:
                            continue
                        old_value = old_threshold[field]
                        new_value = new_threshold.get(field)
                        valid = lambda x: not isinstance(x, bool) and isinstance(x, Real) and math.isfinite(x)
                        if (not valid(old_value) or not valid(new_value) or
                            (new_value < old_value if field == "min" else new_value > old_value)):
                            problems.append(f"ratchet: weakened {kind} {identity} {field}")
                    if old_threshold.get("no_significant_drop") is True and new_threshold.get("no_significant_drop") is not True:
                        problems.append(f"ratchet: removed no_significant_drop for {kind} {identity}")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for rule in spec.get("slices", []):
        name, metric = rule["name"], rule["metric"]
        identifier = f"slice:{name}/{metric}"
        pr_rows = [r for r in pr["rows"] if name in (r.get("slices") or [])]
        base_rows = [r for r in base["rows"] if name in (r.get("slices") or [])]
        pr_pairs = [(r.get("item_id"), r.get("seed")) for r in pr_rows]
        base_pairs = [(r.get("item_id"), r.get("seed")) for r in base_rows]
        invalid = any(not isinstance(r.get(metric), Real) or not math.isfinite(r[metric])
                      for r in pr_rows + base_rows)
        a = {} if invalid else per_item(pr, metric, slice_name=name)
        b = {} if invalid else per_item(base, metric, slice_name=name)
        missing = (invalid or not pr_rows or not base_rows or len(pr_pairs) != len(set(pr_pairs))
                   or len(base_pairs) != len(set(base_pairs)) or set(pr_pairs) != set(base_pairs)
                   or set(a) != set(b) or not a
                   or any(r.get(metric) is None for r in pr_rows + base_rows))
        note = ""
        if missing:
            verdict = "missing"
            value = None
        else:
            keys = sorted(a)
            value = sum(a[k] for k in keys) / len(keys)
            verdict = "fail" if "min" in rule and value < rule["min"] else "ok"
            if rule.get("no_significant_drop"):
                try:
                    delta, lo, hi = stats.paired_bootstrap(
                        [a[k] for k in keys], [b[k] for k in keys],
                        n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                        confidence=bs.get("confidence", 0.95))
                    note = f"delta {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                    if hi < 0:
                        verdict = "fail"
                except ValueError:
                    verdict = "missing"
                    note = "insufficient paired data"
        if verdict != "ok" and rule.get("blocking"):
            blocked.append(identifier)
        label = "ok" if verdict == "ok" else ("BLOCK" if rule.get("blocking") else "warn")
        lines.append(f"  {identifier:<32} {str(value):<8} {note:<30} {label} ({verdict})")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        base_val = base["metrics"].get(mid)
        invalid_metric = lambda x: isinstance(x, bool) or not isinstance(x, Real) or not math.isfinite(x)
        if invalid_metric(val) or invalid_metric(base_val):
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and verdict != "missing":
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
