# Execution checkpoint: 2026-10-14

Continue `rend2-v4-4-6-clean-optimization` from builder commit
`f56275b6c066d290e5d9bf3eb3f87820661f0f9a`. The uploaded comprehensive master task
remains the acceptance contract. No main edit, merge, historical-release
replacement or second production workflow is authorized by this checkpoint.

## Changes actually made in this checkpoint

- `validate_source.py`: detect added/deleted files, restrict the tracked delta,
  reject untracked source, check the locked baseline Git tree, and report the
  three modified GLSL files as NOT byte-identical. Existing functional source
  checks remain. Explicit failures work even with Python assertions disabled.
- `compare_regressions.py`: require the complete 128+16+16+16 capture population,
  paired PNG/TGA pixels, ready/exit status, dimensions, matching A/B settings and
  hardware, and distinct Rend2 binary identities. Inherited analyzer failures
  remain explicit NOT_ACCEPTED semantic results. No-new-failures is not full
  visual acceptance, especially with unsynchronized animation/exposure.
- `test_validation_guards.py`: 23 tests covering valid synthetic inputs and
  missing/extra/corrupt capture evidence, wrong renderer identity, incomplete
  scenarios, source deletion/addition, new and inherited analyzer failures.
- Existing production YAML: run these tests normally and with `python3 -O`
  before source reconstruction; show source/regression results in the summary.

## Local execution evidence

Both `python3 test_validation_guards.py` and
`python3 -O test_validation_guards.py` completed: 23 tests, OK in each invocation.
`python3 -m py_compile` passed. Workflow YAML parsing and shell syntax are checked
separately before pushing. Tiny synthetic unit images exist only in temporary
folders and are deleted by the tests; they are never gameplay screenshots or
production evidence.

GitHub connector access works. Direct container Git clone failed with
`Could not resolve host: github.com`; the container has no MinGW/Wine/Codex
executable. Consequently this local checkpoint does not claim engine source
reconstruction, Windows compilation or actual game execution. Those checks must
be read from the subsequent GitHub workflow, not inferred from the unit tests.

## Scope deliberately preserved

No renderer patch, shader transformation, quality preset, shadow budget or game
logic is changed by this checkpoint. The prior two CPU changes and four shader
transformations still require their actual reconstructed-source tests and CI.
`r_forceSun=1`, `r_dlightMode=2`, StaticPromote maximum 32 and persistent shadow
slots 3 remain as previously configured. The inherited preset explicitly has
SSAO=0 and indirectLighting=0; this is not silently described as all effects on.
No unrelated fire-leak experiment is imported into this branch.

## Acceptance status

Only the new validation-guard unit tests have a new local PASS at this point.
Windows runtime, gaming-GPU performance, complete visual acceptance and the final
release remain unverified. No FPS benefit is asserted. The existing workflow
must produce a clean candidate and authentic evidence, or an explicit failure.
Its run ID, terminal result and artifact ID must be fetched after execution.
