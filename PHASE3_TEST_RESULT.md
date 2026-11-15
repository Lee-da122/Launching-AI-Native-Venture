# Phase 3 Multi-Source Test Result

Controlled local tests completed after adding the WEVITY supplementary source.

- K-Startup parser: 8/8 PASS
- WEVITY saved-fixture listing/detail parser: PASS
- Same-source idempotency: PASS
- Same-source update-in-place: PASS
- Cross-source conservative deduplication: PASS
- Existing competition/team relationship safety: PASS
- One-source failure isolation: PASS
- All-source failure preserves stored data: PASS
- Deadline future/today/past/unknown behavior: 4/4 PASS
- Session 8 normal regression: 10/10 PASS
- Session 8 attack regression: 5/5 PASS
- Phase 2 regression suite: PASS

Important limitation: live WEVITY HTML fetching/parsing was not executed from this local build environment because outbound DNS is unavailable here. Live-source verification must be performed after deployment from Railway before claiming production ingestion is verified.

## Production title parsing regression fix
- Fixed WEVITY title extraction after production showed the shared page heading (`공모전 대외활동 콘테스트 메인메뉴`) as every competition title.
- Collector now prefers the already-parsed listing title when parsing each detail page.
- Added a controlled fixture where the detail page heading is generic but the listing title is a real competition title.
- Result: PASS; existing Session 8 and Phase 2 regressions remain PASS.
