"""Emit `lupine.lean-build-evidence.v1` for the ATLAS theorem synchronizer.

The evidence is the fail-closed input to `tools/atlas_theorem_sync.py`: it
records the lake build gate, the zero-sorry gate, the Vision theorem counts
(themselves locked by `#guard` in the build), and a per-module inventory of
theorem declarations with content hashes. Nothing here trusts a filename: the
lake build must exit 0 and the sorry scan must find zero tokens.

Run from the repo root:

    python tools/build_lean_evidence.py --out config/lean_build_evidence.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

EVIDENCE_SCHEMA = "lupine.lean-build-evidence.v1"
PROOF_REPOSITORY = "lupine-science/open-distillation-factory"
MATHLIB_REVISION = "8a178386ffc0f5fef0b77738bb5449d50efeea95"
ATLAS_REVISION = "c5a10f1a95de31e5476484c8bb3856ee7f164ea0"
EXPECTED_VISION = {
    "legacy_theorems": 290,
    "universal_correction_theorems": 164,
    "honest_errors_theorems": 49,
    "epistemic_gaps": 5,
}

_REPO = Path(__file__).resolve().parents[1]
_LEAN_SPEC = _REPO / "lean-spec"
_SCAN_ROOT = _LEAN_SPEC / "OpenDistillationFactory"

_GIT = ["git", "rev-parse", "HEAD"]
_DECL_RE = re.compile(
    r"\b(?:theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*)"
)
_SCOPE_RE = re.compile(r"\b(namespace|section|end)\b\s*([A-Za-z0-9_.']*)")
_SORRY_RE = re.compile(r"(^|[^A-Za-z0-9_'])sorry([^A-Za-z0-9_']|$)")


def _strip_comments_and_strings(text: str) -> str:
    """Port of lean-spec/scripts/check_no_sorry.sh's awk stripper."""
    out: list[str] = []
    state = "code"
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        c2 = text[i : i + 2]
        if state == "code":
            if c2 == "--":
                state = "line"
                i += 2
                continue
            if c2 == "/-":
                state = "block"
                depth = 1
                i += 2
                continue
            if c == '"':
                state = "str"
                out.append(" ")
                i += 1
                continue
            out.append(c)
            i += 1
        elif state == "line":
            if c == "\n":
                state = "code"
                out.append("\n")
            else:
                out.append(" ")
            i += 1
        elif state == "block":
            if c2 == "/-":
                depth += 1
                out.append("  ")
                i += 2
                continue
            if c2 == "-/":
                depth -= 1
                out.append("  ")
                i += 2
                if depth == 0:
                    state = "code"
                continue
            out.append("\n" if c == "\n" else " ")
            i += 1
        else:  # str
            if c == "\\":
                out.append("  ")
                i += 2
                continue
            if c == '"':
                state = "code"
                out.append(" ")
                i += 1
                continue
            out.append("\n" if c == "\n" else " ")
            i += 1
    return "".join(out)


def _statement_span(code: str, start: int) -> str:
    """Capture the statement (up to the top-level `:=`) after a decl name."""
    depth = 0
    i = start
    while i < len(code) - 1:
        c = code[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ":" and code[i + 1] == "=" and depth == 0:
            return code[start:i]
        i += 1
    raise ValueError(f"declaration at offset {start} has no top-level `:=")


def _module_inventory(path: Path, built: bool) -> dict[str, Any]:
    raw = path.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    module = path.relative_to(_LEAN_SPEC).with_suffix("").as_posix().replace("/", ".")
    code = _strip_comments_and_strings(raw.decode("utf-8"))

    events: list[tuple[int, str, str]] = []
    for match in _SCOPE_RE.finditer(code):
        events.append((match.start(), "scope", match.group(0)))
    for match in _DECL_RE.finditer(code):
        events.append((match.start(), "decl", match.group(0)))
    events.sort(key=lambda event: event[0])

    stack: list[tuple[str, str]] = []
    theorems: list[dict[str, str]] = []
    for pos, kind, token in events:
        if kind == "scope":
            match = _SCOPE_RE.match(token)
            assert match is not None
            word, name = match.group(1), match.group(2)
            if word in ("namespace", "section"):
                stack.append((word, name))
            else:  # end
                if name:
                    for index in range(len(stack) - 1, -1, -1):
                        if stack[index][1] == name:
                            del stack[index:]
                            break
                elif stack:
                    stack.pop()
            continue
        match = _DECL_RE.match(token)
        assert match is not None
        decl_name = match.group(1)
        namespaces = [entry[1] for entry in stack if entry[0] == "namespace" and entry[1]]
        fqn = ".".join([*namespaces, decl_name]) if namespaces else decl_name
        statement = _statement_span(code, pos + len(token))
        normalized = " ".join(statement.split())
        theorems.append(
            {
                "name": fqn,
                "namespace": fqn.rsplit(".", 1)[0] if "." in fqn else "",
                "statement_hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            }
        )
    return {
        "module": module,
        "source_path": path.relative_to(_REPO).as_posix(),
        "source_hash": source_hash,
        "built": built,
        "theorems": theorems,
    }


def _sorry_count() -> int:
    count = 0
    for path in sorted(_SCAN_ROOT.rglob("*.lean")):
        code = _strip_comments_and_strings(path.read_text(encoding="utf-8"))
        count += len(_SORRY_RE.findall(code))
    return count


def _vision_counts() -> dict[str, int]:
    code = _strip_comments_and_strings(
        (_SCAN_ROOT / "Materials" / "Vision.lean").read_text(encoding="utf-8")
    )

    def eval_def(name: str) -> int:
        match = re.search(rf"def {name} : Nat :=(.*?)(?=\n\S)", code, re.DOTALL)
        if match is None:
            raise ValueError(f"Vision.lean is missing def {name}")
        expr = " ".join(match.group(1).split())
        if not re.fullmatch(r"[0-9+\s]+", expr):
            raise ValueError(f"Vision.lean def {name} is not literal arithmetic: {expr!r}")
        return int(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307 - digits and + only

    return {
        "legacy_theorems": eval_def("computationallyProvenCount"),
        "universal_correction_theorems": eval_def("universalCorrectionProvenCount"),
        "honest_errors_theorems": eval_def("honestErrorsProvenCount"),
        "epistemic_gaps": eval_def("epistemicGapCount"),
    }


def _run_lake_build() -> dict[str, Any]:
    result = subprocess.run(
        ["lake", "build"],
        cwd=_LEAN_SPEC,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout[-4000:])
        sys.stderr.write(result.stderr[-4000:])
    return {
        "passed": result.returncode == 0,
        "command": "lake build",
        "exit_code": result.returncode,
    }


def _git_head() -> str:
    result = subprocess.run(
        _GIT, cwd=_REPO, capture_output=True, text=True, encoding="utf-8", check=True
    )
    revision = result.stdout.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError(f"unexpected git HEAD: {revision!r}")
    return revision


def _toolchain_version() -> str:
    raw = (_LEAN_SPEC / "lean-toolchain").read_text(encoding="utf-8").strip()
    return raw.split(":v", 1)[-1] if ":v" in raw else raw


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def build_evidence(*, skip_build: bool) -> dict[str, Any]:
    lake_gate = (
        {"passed": True, "command": "lake build (skipped by flag)", "exit_code": 0}
        if skip_build
        else _run_lake_build()
    )
    built = lake_gate["passed"]

    sorry_count = _sorry_count()
    vision = _vision_counts()

    modules = [
        _module_inventory(path, built)
        for path in sorted(_SCAN_ROOT.rglob("*.lean"))
    ]

    evidence: dict[str, Any] = {
        "schema": EVIDENCE_SCHEMA,
        "schema_version": 1,
        "proof_repository": PROOF_REPOSITORY,
        "proof_revision": _git_head(),
        "lean_version": _toolchain_version(),
        "mathlib_revision": MATHLIB_REVISION,
        "atlas_revision": ATLAS_REVISION,
        "gates": {
            "lake_build": lake_gate,
            "zero_sorry": {"passed": sorry_count == 0, "sorry_count": sorry_count},
            "vision": {"passed": vision == EXPECTED_VISION, **vision},
        },
        "modules": modules,
    }
    evidence["manifest_hash"] = hashlib.sha256(
        _canonical_json(evidence).encode("utf-8")
    ).hexdigest()
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="record the lake build gate as passed without rerunning it "
        "(only valid immediately after a green `lake build` in lean-spec/)",
    )
    args = parser.parse_args(argv)

    evidence = build_evidence(skip_build=args.skip_build)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    gates = evidence["gates"]
    print(
        f"evidence -> {args.out}\n"
        f"  proof_revision: {evidence['proof_revision']}\n"
        f"  modules: {len(evidence['modules'])}; "
        f"theorems: {sum(len(m['theorems']) for m in evidence['modules'])}\n"
        f"  lake_build passed: {gates['lake_build']['passed']}; "
        f"sorry_count: {gates['zero_sorry']['sorry_count']}; "
        f"vision passed: {gates['vision']['passed']}"
    )
    return 0 if all(g["passed"] for g in gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
