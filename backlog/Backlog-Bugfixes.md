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


## Bugfix Verifications Pending (Do not remove this chapter — even if empty) + Testing Todos


## New Bugs (Do not remove this chapter — even if empty)

- [ ] SOC line shows a vertical part near 11:00. Here is the dump: "chart_debug_review\debug_dump_20260724_110005"
- [ ] faulty Recognition of still connected EV (since last charging) is not leading to a proper scheduling (because EV is still fully charged but Earnie thinks that it must be charged again). Problem in the actual setting ist, that there is no trustable information about the real SOC of EV. Are there still possibilities for improvement or is real SOC a necessity?
- [ ] Do a profiling on rendering of "Detaillierte Simulationsansicht" - look for speed up potentials


## Organizational Changes - no bugs (but still no development issue)
