# OpenMontage pipeline/checkpoint findings — 2026-07-21

> Scope: real bugs/gaps in the **OpenMontage codebase and skill docs** (`lib/checkpoint.py`,
> `skills/pipelines/explainer/*.md`), found while properly closing the `scene_plan` gate on
> `projects/canton-vs-east-india-company/` after it had sat `awaiting_human` since 07-18 while
> downstream work proceeded anyway.
>
> **This is deliberately separate from that project's own content.** Nothing here belongs in a
> writeback for the video production itself — this file is scoped for a future PR against
> upstream `calesthio/OpenMontage` (confirmed real remote, current local branch `feat/tts-preprocess`).
> Each finding below was independently re-verified by a fresh agent that re-read the current source
> from scratch (not trusting the original discovery) before being recorded here — see verdicts.
>
> Status: all 5 candidates **CONFIRMED**, all marked **upstream-PR-worthy**. All 4 issues and PRs
> below are now real and open against `calesthio/OpenMontage` (Finding B was downgraded to a
> docs-only fix after its original hard-validation draft broke 13 existing tests — see its section).
>
> | Finding | Issue | PR | Status |
> |---|---|---|---|
> | A — sequence gate | [#414](https://github.com/calesthio/OpenMontage/issues/414) | [#418](https://github.com/calesthio/OpenMontage/pull/418) | open, mergeable |
> | E — style_playbook validation | [#415](https://github.com/calesthio/OpenMontage/issues/415) | [#419](https://github.com/calesthio/OpenMontage/pull/419) | open, mergeable |
> | B — pipeline_dir docs (downgraded) | [#416](https://github.com/calesthio/OpenMontage/issues/416) | [#420](https://github.com/calesthio/OpenMontage/pull/420) | open, mergeable |
> | C + D — explainer docs | [#417](https://github.com/calesthio/OpenMontage/issues/417) | [#421](https://github.com/calesthio/OpenMontage/pull/421) | open, mergeable |
>
> All 4 branches were verified against the real test suite (pulled via a tarball snapshot + local-only
> git, since `git clone`/SSH to github.com were failing with `SSL_ERROR_SYSCALL` in this network this
> session — pushed to the fork via the GitHub Git Data API instead, which worked fine over plain HTTPS).

---

## Finding A — `write_checkpoint()` never checks that earlier gated stages are approved

**Severity: medium · File: `lib/checkpoint.py` · The root cause of this session's original problem**

`write_checkpoint()` enforces that the **stage currently being written** can't be `status="completed"`
without `human_approved=True` (the existing "GATE VIOLATION" check, lines 378–405). But nothing checks
whether **earlier stages** in the pipeline sequence are actually approved before allowing a write to a
**later** stage. `_stage_requires_approval()` only resolves the gate policy for the one stage passed in;
`get_pipeline_stages()` is used only to validate the stage name is legal, never to check ordering.
Sequence-aware helpers (`get_completed_stages()`, `get_next_stage()`) exist but `write_checkpoint()`
never calls them — they're advisory, described in `skills/meta/checkpoint-protocol.md` as something the
*agent* should check, not something the *writer* enforces.

**Empirical proof**: `projects/canton-vs-east-india-company/checkpoint_scene_plan.json` sat
`status="awaiting_human"`, `human_approved=false` continuously from 2026-07-18 through today — three
rewrites, never once approved — while `checkpoint_assets.json`/`checkpoint_edit.json`/`checkpoint_compose.json`
were all written on 2026-07-19 with no error. The bridge script that wrote them (in this same project)
explicitly relies on this gap, using `status="in_progress"` specifically to avoid triggering the
existing same-stage check. `tests/backlot/test_gate_scenarios.py` only covers same-stage violations —
no test exercises predecessor-stage validation, confirming this was never a tested invariant.

**Proposed fix**: add a `_first_unapproved_predecessor()` helper that walks `get_pipeline_stages(pipeline_type)`
up to the stage being written, and for each gated predecessor reads its checkpoint via `read_checkpoint()`;
if any predecessor isn't `completed`+`human_approved`, `write_checkpoint()` raises a new
`"SEQUENCE GATE VIOLATION"` `CheckpointValidationError` — but **only when `status != "in_progress"`**,
so existing resume/liveness heartbeats (and this project's own bridge-script pattern) keep working.
Add tests to `tests/backlot/test_gate_scenarios.py` mirroring the existing same-stage test, asserting
the new check fires for `completed`/`awaiting_human` writes but not for `in_progress`.

Full proposed patch (helper + call site + test plan) is in the verification agent's output —
available on request when this becomes a real PR.

---

## Finding B — `write_checkpoint()`/`_checkpoint_path()` never validates `pipeline_dir` resolves to a real project

**Severity: low (latent footgun, not yet an observed production defect) · File: `lib/checkpoint.py`**

`_checkpoint_path(pipeline_dir, project_id, stage)` is pure path arithmetic
(`pipeline_dir / project_id / f"checkpoint_{stage}.json"`) with zero validation. `write_checkpoint()`
then does `path.parent.mkdir(parents=True, exist_ok=True)` unconditionally. If a caller passes the
**project's own directory** as `pipeline_dir` instead of its parent (the projects root) — an easy
mistake, since neither the function's one-line docstring, `_checkpoint_path`'s (nonexistent) docstring,
nor `AGENT_GUIDE.md` (which never uses the identifier `pipeline_dir` at all) states the expected
semantics — it silently creates a wrong, doubly-nested directory tree instead of failing loudly. Hit
this exact bug live this session while writing this project's own gate-closure script.

Mitigating context: every current production caller (`scripts/backlot_simulate_run.py`,
`scripts/backlot_screenshot_stage.py`) passes a fixed root constant, so this hasn't caused an observed
defect in shipped code — it's a latent API footgun that any new script is one typo away from hitting.

**Proposed fix**: before the `mkdir`+write, check `(pipeline_dir / project_id / "project.json").exists()`
and raise a `CheckpointValidationError` naming the expected vs. actual path if not. Add the parameter
contract to `write_checkpoint`'s docstring and to `AGENT_GUIDE.md` near the existing checkpoint-path
convention note (line ~608).

---

## Finding C — `skills/pipelines/explainer/{idea,script,scene}-director.md` document a submission function that doesn't exist

**Severity: medium · Files: `skills/pipelines/explainer/idea-director.md:132`, `script-director.md:210`, `scene-director.md:229`**

All three tell the agent to "Call `handle_explainer_idea/script/scene_plan(state, {...})` to validate
and persist." No function with any of those names (or a close variant) exists anywhere in the repo
(`grep -rn "def handle_"` across all `.py` files returns zero matches). This is a **localized** defect,
not a repo-wide convention: all 12 pipelines' other director docs — including explainer's own
`asset-director.md`, `edit-director.md`, `compose-director.md`, `publish-director.md`,
`proposal-director.md`, and `research-director.md` — correctly say "validate against the schema and
persist via checkpoint," describing the real, implemented, tested mechanism
(`lib/checkpoint.py::write_checkpoint()` + `validate_artifact()`).

**Proposed fix**: edit the three affected lines to match the convention used everywhere else in the
same file family, e.g. replace the fictitious call with "Validate the scene_plan against the schema
and persist via checkpoint" (identical wording already used in `talking-head/scene-director.md:243`).
Optionally show the real `write_checkpoint(pipeline_dir, project_name, stage_name, status, artifacts)`
call form from `skills/meta/checkpoint-protocol.md` Step 3 for concreteness — but don't invent a
per-pipeline wrapper name that doesn't exist.

---

## Finding D — explainer's `scene-director.md` Scene Types table conflates two incompatible vocabularies

**Severity: medium · File: `skills/pipelines/explainer/scene-director.md:66-87` vs. `schemas/artifacts/scene_plan.schema.json:18-21`**

The schema's real `type` enum for a scene has 9 values: `talking_head, broll, animation,
character_scene, diagram, text_card, transition, generated, screen_recording`. But the skill's "Scene
Types and When to Use Them" table lists 16 names under a header that reuses the same `type` field name,
9 of which (`hero_title, stat_card, bar_chart, line_chart, pie_chart, kpi_grid, comparison, callout,
progress_bar`) **aren't valid schema values at all** — confirmed empirically: constructing a scene with
`"type": "stat_card"` and running it through `jsonschema.validate()` raises
`'stat_card' is not one of [...]`. Root cause: those 9 names are actually the **downstream** `cut.type`
vocabulary consumed later by the Edit stage / `video_compose.py` / `remotion-composer/SCENE_TYPES.md` —
a real, different, valid vocabulary — but presented in this table as if it belonged to the Scene
Planner's own artifact. This conflation exists only in the `explainer` pipeline; none of the other 11
pipelines' `scene-director.md` files have this pattern.

**Proposed fix**: rename the table header from `Type` to `Render Template (cut.type at Edit stage)`,
add a sentence clarifying these are Remotion render-template names for the Edit stage's `cuts[].type`
— not valid values for this scene's own `type` field — and add a mapping from each of the 9 mismatched
names to the correct `scene_plan.type` enum value a planner should actually use.

---

## Finding E — `init_project()`/`write_checkpoint()` never validate `style_playbook` names a real file

**Severity: medium · File: `lib/checkpoint.py` (both `init_project()` and `write_checkpoint()`)**

`style_playbook` is accepted and written verbatim with no existence check against `styles/*.yaml`.
Confirmed empirically on this exact project: `project.json` declares
`"style_playbook": "great-war-map-ui+engraving-hero"`, but `styles/` contains only
`anime-ghibli.yaml, clean-professional.yaml, flat-motion-graphics.yaml, minimalist-diagram.yaml,
premium-minimalist.yaml` — no match, and `"+"` isn't a supported composite-playbook syntax anywhere in
the codebase (`playbook.schema.json` models one playbook as one monolithic object;
`playbook_loader.load_playbook()` does exact `f"{name}.yaml"` lookup and raises `FileNotFoundError` if
missing). The real-world effect isn't a crash: every downstream consumer
(`tools/video/video_compose.py:1062-1067`, `:1545-1550`) wraps the load in a bare
`try/except Exception: pass`, so a bad `style_playbook` name silently degrades to default styling with
**no warning anywhere** — not in logs, not in the checkpoint, not in the Backlot dashboard (which reads
the same unchecked string straight from `project.json`). This production has been running its entire
lifecycle citing a style playbook that was never actually written, silently defeating
`scene-director.md` Step 5's "Validate Against Playbook" requirement.

**Proposed fix** (two complementary, both upstream code changes):
1. In `lib/checkpoint.py`, add an existence check in both `init_project()` and `write_checkpoint()`
   wherever `style_playbook` is accepted — raise `CheckpointValidationError` listing available
   playbooks if the name doesn't resolve to a real `styles/{name}.yaml`, mirroring the existing
   fail-closed pattern already used for a typo'd `pipeline_type`.
2. Harden the two silent-swallow sites in `video_compose.py` to log a warning instead of silently
   passing, as defense-in-depth for checkpoints written before the new check exists.

---

## Suggested PR split

These don't need to land as one PR — natural boundaries:

1. **Finding A** (sequence gate) — the highest-value, most self-contained fix; ships with its own test.
2. **Finding E** (style_playbook validation) — same shape/pattern as A (fail-closed on an unchecked
   string), could ship together with A or separately.
3. **Finding B** (pipeline_dir validation) — smallest, lowest-risk, good first PR if wanting something
   trivial to land first.
4. **Findings C + D** — pure documentation fixes inside `skills/pipelines/explainer/`, zero code risk,
   could ship as one small doc-only PR.

No fixes have been applied to the OM codebase yet as of this writing — this file is the complete,
independently-verified findings record to work from when that PR work happens.
