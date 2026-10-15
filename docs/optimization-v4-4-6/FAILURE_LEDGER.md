# Failure ledger

| Stage | Evidence | Root cause | Resolution |
|---|---|---|---|
| Local MinGW install | apt update setgroups/seteuid failure | Runtime cannot switch to apt service user | Use normal GitHub Ubuntu runner; no sandbox bypass |
| Git push dry-run | could not read Username | No shell GitHub write credential | Use connected GitHub Git-object APIs; no token extraction |
| Baseline source audit | telemetry workflow omits v4.4.3 AA + UI deltas | Historical release assembled from separate module builds | Component-specific versioned reconstruction, source-tree gate |
| Workflow launch capability | No connector workflow-dispatch endpoint exposed | Tool capability limitation | One branch-and-path-scoped push trigger, no recursive commits |

| Run 38150934190 native smoke | Both Win64 builds/package PASS; 4/6 baseline captures black or pre-READY | `wait 180` also advances during loading/briefing; command-line screenshot/quit raced gameplay | Diagnostic-only capture now waits for playerstart and 32 rendered gameplay scenes; production binaries untouched. Re-run required. |

No historical 37678074243/37682884950 downloads are needed. No production branch changes are authorized or performed.

Diagnostic compatibility review found TestLab still referenced `activeCount` removed with the dead production report. The diagnostic-only adapter now calculates the emission delta on both variants; early native syntax checks cover both fully instrumented source copies.

Run 38152560928: both Win64 builds/package PASS. Five baseline map captures now SMOKE_PASS. SWF reached real gameplay but screenshot at game time 3509 was 94.43% near-black; retained FAIL. Diagnostic capture now additionally waits at least 6 seconds of gameplay and zero cgame fadeRate. The image threshold remains unchanged.

Runtime log review exposed startup preset contamination: fresh homes queue `highVidhighCPU.cfg` through `Com_SetRecommended`, even under +safe. The launcher and diagnostic command now set `com_recommendedSet=1` as a startup variable, before Com_Init schedules recommendations. Runtime capture validates actual quality cvars against the selected preset; no quality downgrade is accepted.
