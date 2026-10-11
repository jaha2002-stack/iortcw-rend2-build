# Failure ledger

| Stage | Evidence | Root cause | Resolution |
|---|---|---|---|
| Local MinGW install | apt update setgroups/seteuid failure | Runtime cannot switch to apt service user | Use normal GitHub Ubuntu runner; no sandbox bypass |
| Git push dry-run | could not read Username | No shell GitHub write credential | Use connected GitHub Git-object APIs; no token extraction |
| Baseline source audit | telemetry workflow omits v4.4.3 AA + UI deltas | Historical release assembled from separate module builds | Component-specific versioned reconstruction, source-tree gate |
| Workflow launch capability | No connector workflow-dispatch endpoint exposed | Tool capability limitation | One branch-and-path-scoped push trigger, no recursive commits |

No historical 37678074243/37682884950 downloads are needed. No production branch changes are authorized or performed.
