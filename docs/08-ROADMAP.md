# Delivery roadmap (sequence, not time promise)
| Gate | Scope | Exit evidence |
|---|---|---|
| G0 Spike | FND, UI foundation, bridge, Windows offline packaging | Small real end-to-end native app with DB and export; version locks |
| G1 Core | CFG, MST, EVT | Onboarding/import 3 school types; no data collisions |
| G2 Automation | SES, ROM, SCH | Independent solver validation; review & lock; infeasible recovery |
| G3 Pilot | DOC P0, TPL P0, BAK P0, QA, REL | 3 schools test actual workflow; primary docs printable; no data loss |
| G4 Operations | COM, TSK, EXP, OPS | Full cycle and audit; actual presences; susulan |
| G5 Finance & reporting | FIN, LPJ, ARC, branding, remaining documents | Reconcile LPJ with ledger & actual data; archive replay |
| G6 Commercial | LIC, REL, all P1, UAT | Signed-off v1 scope, installer offline; pricing Rp150k |
| G7 Enhancements | P2 visual template canvas, advanced features | Prioritized by pilot feedback |

P0 tasks can include infrastructure used later; P1 tasks only after dependencies. Implement vertical slices; each issue has one small reviewable change, not module mega-PR. Estimate using S/M/L after spike; no fixed calendar before measurements. Track progress from checklist evidence not number of generated files. At each gate update CHANGELOG, decision log and outstanding risks. Pilot can run before LPJ/finance exists only if communicated.
