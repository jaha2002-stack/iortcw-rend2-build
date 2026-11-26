# Performance A/B

GPU_DATA_UNAVAILABLE. No target Windows GPU runner or authenticated local-PC execution tool is available in this session. No real-PC telemetry capture was supplied. No game p50/p95/p99, 1% low, 75 FPS or whole-frame percentage claim is made.

The C harness compares actual extracted baseline/optimized functions with UBSan. It measures deterministic operation counts, not elapsed GPU/frame time. See algorithm-equivalence.json for 850000 label checks and 10000 light emission cases.

A qualifying next measurement uses identical SHA/settings/map/camera/driver/hardware, warmup, >=3 runs/variant, alternating order. DWPERF probe=1 frames must be excluded from normal frame-time statistics. Acceptance requires variance-aware improvement and no significant critical-scene regression; initial 5% hot-path / 3% p95 thresholds from the task apply only above measured noise.

Linux Mesa smoke, when available, is software compatibility evidence only. Spawn screenshots with dynamic simulation are not pixel-exact temporal A/B acceptance.
