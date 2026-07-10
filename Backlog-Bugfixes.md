# Open Bugs

Completed items → [Backlog-Erledigt.md](Backlog-Erledigt.md) (sections `### Bugfix …` / regressions)

Feature roadmap → [Backlog.md](Backlog.md)

## Classification

**Here:** Prod deviation, regression (`xfail`), known misbehavior, review with clear fix/remove outcome.
**Not here:** New behavior, UX, models, research — see feature backlog in `Backlog.md`.
**Versioning:** completed bugfixes → **PATCH** only in `version.py` (no minor bump).

### `## Bugfix Verifications Pending`

Fix is **implemented** (code + tests + optional PATCH in `version.py`), but **prod/live acceptance** is still pending.

- Move item from the thematic bugfix chapter here once the fix is committed — **not** directly to `Backlog-Erledigt.md`.
- Briefly note what changed (commit/version) if helpful.
- After successful verification: remove from this chapter → `Backlog-Erledigt.md` (`### Bugfix …`) with `- [x]`.
- If verification fails: return to open bugfix chapter or formulate follow-up; document PATCH if applicable, but do not archive as done.


## New Bugs (Do not remove this chapter — even if empty)

## Bugs after testing 1.25.0
- [ ] Query Loxone credentials only when live operation is enabled and markers should be verified (defer to later)


## EV: urgent rule, prod dump, PWM
Related topics — prioritize and work through together.

- [ ] **Review urgent rule for necessity** (review by approx. **2026-07-12**)
  - Evaluation: `urgent_rule_observability` in log + `optimization_history.jsonl` (`role`: `redundant` / `nachholen` / `nur_urgent_fenster`)
  - Acceptance: consistently only `redundant` → remove constraint; otherwise keep and justify
- [ ] **Prod-dump regression: urgent constraint infeasible** (as of 2026-07-03, commit `a743318`)
  - Fixture: `eauto_urgent_deferred_cheap_hours_2026-06-28` (~7.99 kWh remaining)
  - Live mode A: MILP with urgent → **Infeasible**; without urgent → **Optimal**
  - `@pytest.mark.xfail` in `tests/test_prod_dump_regression.py` (2 tests)
  - Next step: verify live urgent + mode A; remove `xfail` when feasible
- [ ] **PWM for EV charging** — only for currents < A_min; otherwise minimum charge amount per h (count down meter, reset on each charge → at zero charge five minutes at minimum current)
