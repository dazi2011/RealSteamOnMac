# Project History

This document preserves the engineering history that previously dominated the
README. Current user installation and feature documentation lives in
`README.md` and `README.zh-CN.md`.

## Milestones

1. Audited and recovered the original Steam patching prototype with complete
   rollback snapshots.
2. Isolated a startup compatibility-tool discovery path that removed Steam
   Cloud settings on macOS build `1780705203`.
3. Added a delayed authenticated native registry for all owned visible
   Windows-only games while excluding native and dual-platform macOS titles.
4. Built immutable Wine/GPTK/DXMT/DXVK/WineD3D runtime packages and a real
   Proton `lsteamclient` bridge.
5. Added per-game compatibility settings, dependency installation, run-command
   jobs, Windows 10 prefixes, and recoverable container actions.
6. Completed live GPTK, DXMT, DXVK macOS, and WineD3D game launches with normal
   exit and Steam AutoCloud.
7. Replaced the large cross-window dashboard with compatibility-page-only
   Steam-style rows and side-by-side tool discovery from
   `compatibilitytools.d`.
8. Added automatic backups, reversible uninstall, signed update manifests, and
   install/uninstall PKG workflows.
9. Added UUID-, hash-, and instruction-verified profiles for Steam Public Beta
   builds `1780705203` and `1780965181`, while preserving fail-closed behavior
   for unknown builds and stale rollback snapshots.
10. Added build `1781212412`, a distinct transactional Update.pkg, and
    failure rollback that preserves game depots, PFX containers, user tools,
    and per-game configuration.

## Detailed Records

- Current plans: `docs/superpowers/plans/`
- Design specifications: `docs/superpowers/specs/`
- Runtime and renderer research: `docs/research/`
- Dated handoffs and live evidence: `docs/handoff/` and `docs/evidence/`
- Running implementation journal: `progress.md`
- Root-cause and architecture findings: `findings.md`
- Full phase checklist: `task_plan.md`
