# AGENTS.md — End-to-End Development Workflow

This project ships with a curated set of agent **skills** (see `.agents/skills/`, pinned in
`skills-lock.json`). This file defines the standard development workflow built on top of them.

**Project:** MediaPipe-based exercise-repetition counter (ComVis). Real-time pose/landmark
inference → repetition counting. Stack is Python + MediaPipe (C++ core).

**Golden rule:** At every phase, respect the project's domain model and past decisions —
read `CONTEXT.md` (if present) for the ubiquitous language and `docs/adr/` for architectural
decisions (ADRs) before designing or touching code.

---

## Skill map

| Skill | Invocation | Role in workflow |
|---|---|---|
| `wayfinder` | user (`/wayfinder`) | Chart big, foggy efforts into tickets |
| `grilling` / `grill-me` / `grill-with-docs` | user | Stress-test a plan, one question at a time |
| `domain-modeling` | model | Build/keep `CONTEXT.md` glossary + ADRs |
| `research` | model | Delegate reading against primary sources |
| `codebase-design` | model | Deep-module vocabulary & design-it-twice |
| `improve-codebase-architecture` | user | Scan for deepening opportunities → HTML report |
| `tdd` | model | Test-first red→green implementation |
| `diagnosing-bugs` | model | Disciplined bug/perf diagnosis loop |
| `teach` | user (`/teach`) | Teaching workspace for the user |
| `find-skills` | model | Discover/install new skills |
| `writing-great-skills` | user (`/writing-great-skills`) | Reference when authoring skills |

*(User-invoked skills have `disable-model-invocation: true` — call them by name; the rest the
agent reaches on its own or by name.)*

---

## The workflow

### Phase 0 — Intake / Direction  *(when the effort is large or foggy)*
If the request is a loose idea too big for one agent session, run **`/wayfinder`** to chart a
shared map of investigation tickets (grilling + domain-modeling first to pin the *destination*),
then work the frontier one ticket per session. If the path is already clear, skip straight to
Phase 1.

### Phase 1 — Spec & Alignment  *(grilling + domain-modeling)*
Before building anything, run **`/grill-with-docs`** (or `/grilling` + `/domain-modeling`): the
agent interviews you relentlessly, **one question at a time**, proposing a recommended answer for
each, and captures decisions as they crystallise:
- New or sharpened domain terms → written to **`CONTEXT.md`** (glossary only — no implementation).
- Hard-to-reverse, surprising, trade-off decisions → written as **ADRs** in `docs/adr/`.

Use `/grilling` when you don't want docs written. Do **not** implement until shared understanding
is reached.

### Phase 2 — Research  *(research)*
For anything needing external knowledge (MediaPipe APIs, pose models, accuracy trade-offs), use
**`/research`**: a background agent reads **primary sources** (official docs, specs, source),
cites each claim, and writes a Markdown summary into the repo's notes convention. Keep working
while it reads.

### Phase 3 — Architecture & Module Design  *(codebase-design + improve-codebase-architecture)*
1. Run **`/improve-codebase-architecture`** to scan the codebase for **deepening opportunities**
   (shallow modules, hidden coupling, untested seams) and present them as a visual HTML report.
2. For each candidate, grill the design tree together, then apply the **`/codebase-design`**
   vocabulary:
   - Think in **modules** with small **interfaces** sitting at clean **seams**; pursue **depth**
     (leverage for callers, locality for maintainers).
   - Use the **design-it-twice** pattern (parallel sub-agents) to explore alternative interfaces.
   - Apply the **deletion test** and "the interface is the test surface".
3. Keep `CONTEXT.md`/ADRs current as the design evolves.

### Phase 4 — Implementation  *(tdd)*
Build test-first with the **red → green** loop:
- **Confirm seams before any test.** Agree the public interfaces to test at; no test at an
  unconfirmed seam.
- Work in **vertical slices** (one test → one minimal implementation → repeat), never all-tests-first.
- Write the failing test first; ship only enough code to pass; no speculative features.
- Tests verify **behavior through public interfaces**, not internals (no implementation-coupled or
  tautological tests).
- Refactoring is a separate review concern, not part of the loop.

### Phase 5 — Debugging  *(diagnosing-bugs)*
When something is broken or slow, follow the diagnosis loop — no hypotheses before a feedback loop:
1. **Build a tight feedback loop** (failing test, curl, headless script, replay, fuzz…) that goes
   *red* on the exact symptom, fast and deterministic.
2. **Reproduce + minimise** the repro.
3. **Hypothesise** 3–5 ranked, falsifiable hypotheses; show the user.
4. **Instrument** one variable at a time (tag debug logs `[DEBUG-xxxx]`).
5. **Fix** + write a regression test *before* the fix (only at a correct seam; if no seam exists,
   flag the architectural gap).
6. **Cleanup + post-mortem** — remove instrumentation, confirm the repro is gone, and if the
   architecture blocked the regression test, hand off to `/improve-codebase-architecture`.

### Phase 6 — Continuous improvement
Periodically re-run **`/improve-codebase-architecture`** to surface new deepening opportunities as
the codebase grows. Treat architectural friction found during debugging as candidates.

---

## On-demand skills
- **`/teach`** — turn a topic into a teaching workspace (lessons, references, learning records).
- **`/find-skills`** — discover and install skills from the ecosystem (`npx skills find/add`).
- **`/writing-great-skills`** — reference when authoring or editing skills for this project.

## Conventions
- Commits/PRs should state the correct hypothesis (from debugging) and reference ADRs by number.
- Prefer primary sources over blog summaries; cite them in research notes.
- Keep `CONTEXT.md` free of implementation detail — it is a glossary and nothing else.
