---
name: code-review
description: Performs a systematic, critical, skeptical code review of any module/PR in the repo. Scans API design, types, edge cases, error handling, test coverage, documentation, and architectural alignment. Produces a tiered report (Critical→Nit) with actionable fix/test recommendations per finding.
disable-model-invocation: false
---

# Code Review

Systematic review for correctness, robustness, and maintainability.

## When to Use

When the user asks you to:
- "Review this code" / "Code review please"
- "Periksa kode" / "Review" / "Cari gap"
- "Audit" / "Temuan"
- Mentions wanting a critical/skeptical review
- Before merging a PR

## How to use

1. Ask which module/PR to review. If none specified, review the entire recent diff (`git diff HEAD~1`).
2. Load this skill — it installs the review framework below.
3. Read every changed file in full.
4. Write a tiered report (see **Output Format**).

## Systematic Review Dimensions

For every file/module, cross-check these 8 dimensions:

### 1. API Design & Interface Seams
- Is the public interface (Protocol/ABC/exports) minimal? Does it expose internals?
- Are parameter names, types, and semantics crystal clear from the signature?
- Does the interface sit at the right **seam** (architecture.md)? Can it be swapped/mocked cleanly?
- `**Anti-pattern:**` leaking implementation details into the Protocol contract.

### 2. Type Safety & Valid Ranges
- Are `Optional`/`None`-able fields explicitly typed? Are `| None` annotations correct?
- Are numeric ranges enforced at boundaries (e.g., visibility ∈ [0,1], angle ∈ [0,180], image dimensions)?
- Are `dict[int, T]` keys always within the documented legal range (e.g., 0..32 for landmarks)?
- Do enums cover all possible runtime values? Are there missing Enum members?
- `**Anti-pattern:**` leaving `float` unconstrained when domain rules exist (e.g., "must be > depth_threshold").

### 3. Error Handling & Edge Cases
- What happens on: `None` input, empty dict, zero-size array (OpenCV), out-of-range enum?
- Are `KeyError`, `IndexError`, `ValueError` guarded at the boundary or allowed to propagate?
- Does the code crash silently? Does it return a sentinel (None) that callers must handle?
- Are `assert` statements used for preconditions (acceptable in tests) vs validation (should raise)?
- **Anti-pattern:** letting a typing-only assertion (`x: float | None`) pass through to `math.isfinite(x)` without a runtime guard.

### 4. Domain Correctness (project-specific)
- **Angle convention:** interior hip–knee–ankle → ~180° standing, ~90–100° parallel, <90° deep (ADR-0003).
- **Visibility threshold:** `0.5` is the pause gate alignment (ADR-0007-C); thresholds must match between Features and Count.
- **Landmark indices:** LEFT_LEG=(23,25,27) = hip,knee,ankle; RIGHT_LEG=(24,26,28). Never swap.
- **Coords:** world-landmark x/y preferred, z always ignored (ADR-0007-A).
- **Depth definition:** `≤100° = parallel`, `<90° = is_full` (ADR-0003 consensus).
- **Hysteresis:** count only after a full cycle (stand→down→bottom→up→stand), not on any single crossing.
- **Calibration:** auto-calibrated per session; standing_angle must be > depth_threshold + standing_margin.

### 5. Test Coverage & Test Quality
- Are the tests at the correct **seam** (public interface, not internals)?
- Are edge cases covered: empty, too-short, missing landmarks, full dropout, rapid movement, borderline angles (±1° from thresholds)?
- Are the tests **not tautological** (implement the same logic as the code)?
- Do mocked tests capture the right behaviour? (Check: are the fakes faithful to the real API structure?)
- Are integration tests skip-guarded (not fragile) and do they represent real conditions?
- `**Anti-pattern:**` testing a method that panics on None with a helper that never passes None (misses the real bug).

### 6. Arithmetic & Numerical Stability
- Division by zero, `sqrt(negative)`, `acos(out_of_range)`: are these guarded?
- Floating-point comparisons: avoid `==` on floats; use `<=`/`>=` for thresholds.
- EMA: does `abs(angle - smoothed) > jitter_threshold` correctly bypass when delta is large?
- Hysteresis band: are entry and exit thresholds separated by a gap, not touching?

### 7. Performance & Allocation
- Are hot-path allocations (per-frame dicts, lists) bounded?
- Does every frame create new objects vs reusing?
- Is the MediaPipe model loaded once (singleton/reuse) or per-call?
- **4K frames:** are they downscaled before inference?

### 8. Documentation & ADR Alignment
- Do new types, functions, parameters have docstrings explaining *why* (not just *what*)?
- Are design decisions referenced to the relevant ADR number?
- Are changes consistent with CONTEXT.md glossary terms?
- Are research claims cited to specific sources (squat-rep-counting.md §)?

## Finding Classification

| Level | Meaning | Action required |
|---|---|---|
| **🔴 Critical** | Wrong behaviour, crash, silent data corruption | Must fix before merge |
| **🟠 High** | Conceptual gap, weak assumption, missing edge case | Should fix or document as explicit limitation |
| **🟡 Medium** | Test gap, unclear naming, missing error message | Fix if time allows |
| **🔵 Low** | Style, doc typo, minor readability | Nice to fix |
| **⚪ Nit** | Subjective preference, pedantry | Ignore or address at author's discretion |

## Output Format

```
# Code Review: <module/PR name>

Reviewed files: `src/.../`, `tests/.../`

---

## 🔴 Critical

### 1. Title (file:line)
- **Issue:** ...
- **Why:** ...
- **Recommendation:** ...
- **Suggested test:** ...

## 🟠 High

### 1. Title (file:line)
...

## 🟡 Medium

...

## 🔵 Low

...

## ⚪ Nit

...

---

## Summary
- **Critical:** 0 • **High:** X • **Medium:** X • **Low:** X • **Nit:** X
- **Overall verdict:** ✅ / ⚠️ / ❌
```

## Per-finding structure

Every finding must include:

| Field | Required | Description |
|---|---|---|
| **Issue** | ✓ | What is wrong / risky |
| **Why** | ✓ | Why it matters (consequence) |
| **Recommendation** | ✓ | How to fix or mitigate |
| **Suggested test** | ✓ | Concrete test case that would catch or prove this issue |

## Review scope notes

- You may review a full module, a diff, or a single file.
- Always read the full file, not just the diff — context matters.
- When reviewing a PR diff, also read the files *outside* the diff that the changed code calls (dependency drill).
- For the first review of a module, run the full test suite first; note any pre-existing failures.
- When you find a bug, attempt to write a minimal reproduction (a code snippet that demonstrates the failure) before reporting.
