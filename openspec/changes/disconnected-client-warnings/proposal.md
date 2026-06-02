# Proposal: Eliminate Disconnected Client Warnings (Phase 2 — viewer_registry)

## Intent

After Phase 1, operators still trigger "Attempting to send delta to disconnected client" warnings
when taking actions (resume timer, assign score) after closing the public display window.
Root cause: the system publishes snapshots regardless of whether any viewer is actually connected.
Phase 2 eliminates this at the source with an in-memory viewer registry that gates all publishes.

## Scope

### In Scope
- Static `_viewer_registry: dict[str, set[str]]` (display_key → set[client_token]) in `SecondaryDisplayService`
- Lifecycle methods: `register_viewer`, `unregister_viewer`, `has_active_viewers`, `unregister_viewer_by_token`
- Registration on `SecondaryDisplayState.load_display()` (+ heartbeat touch as backup)
- Disconnect unregistration in `SecondaryDisplayState` (Reflex on_disconnect if available)
- Guard in `KataMatchState._publish_display_snapshot()`: skip if no active viewers
- Guard in `KumiteMatchState._publish_display_snapshot()` and `_publish_display_snapshot_background_safe()`
- TDD tests for registry methods and snapshot-skip behavior (RED → GREEN → TRIANGULATE → REFACTOR)
- Autouse pytest fixture to stub `has_active_viewers → True` for all test files except `test_secondary_display_service.py`
- Update `apply-progress.md` with Phase 2 TDD evidence
- Single commit: `feat(display): Phase2 viewer_registry to eliminate disconnected-client warnings`

### Out of Scope
- Persistent storage of viewer state (in-memory only)
- Multi-process or multi-server viewer sync
- Phase 1 behavior changes (Phase 1 guards remain intact)

## Capabilities

### New Capabilities
- `viewer-registry`: In-memory registry that tracks active public display viewers and gates snapshot publishes

### Modified Capabilities
- None (Phase 1 socket-probe guards remain, this adds a faster in-memory layer above them)

## Approach

Add `_viewer_registry` as a class-level dict to `SecondaryDisplayService` (protected by the existing lock or a new `threading.Lock`). On `load_display()` and heartbeat, register the websocket token. On disconnect or TTL expiry, unregister. Before any `publish_snapshot` call in Kata and Kumite states, call `has_active_viewers(display_key, ttl_seconds=5)`. If `False`, return immediately — zero DB writes, zero deltas, zero warnings.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `kakumi_app/services/secondary_display_service.py` | Modified | Add `_viewer_registry`, 4 lifecycle methods |
| `kakumi_app/states/secondary_display_state.py` | Modified | Call `register_viewer` on load + disconnect handler |
| `kakumi_app/states/kata_match_state.py` | Modified | Guard in `_publish_display_snapshot()` |
| `kakumi_app/states/kumite_match_state.py` | Modified | Guards in both publish methods |
| `tests/test_secondary_display_service.py` | New/Modified | 6 registry tests |
| `tests/test_kata_match_state.py` | Modified | Skip-when-no-viewers test |
| `tests/test_kumite_match_state.py` | Modified | 2 skip-when-no-viewers tests |
| `tests/conftest.py` | Modified | Autouse fixture for `has_active_viewers → True` |
| `openspec/changes/disconnected-client-warnings/apply-progress.md` | Modified | Phase 2 TDD evidence |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing tests skip publish because no viewer registered | High | Autouse conftest fixture stubs `has_active_viewers → True` |
| Race between disconnect and publish | Low | Registry uses thread-safe set ops; heartbeat TTL as backup |
| Reflex doesn't expose on_disconnect | Medium | Heartbeat TTL (5s) handles cleanup; document in apply-progress |

## Rollback Plan

`git revert <phase2-commit>` — all changes are isolated to one commit. Phase 1 guards remain unaffected.

## Dependencies

- Phase 1 commit `cb88a8f` must be present in HEAD (verified by verify-report.md)

## Success Criteria

- [ ] `pytest -q tests/test_secondary_display_service.py tests/test_kata_match_state.py tests/test_kumite_match_state.py` → all green
- [ ] `python -m pytest tests -v` → no regressions
- [ ] Zero "Attempting to send delta to disconnected client" warnings when public window is closed
- [ ] Snapshots publish normally when at least one viewer is connected
