# DarkWolf Android Graphics Lab V01 (experimental)

**Exact requested parent:** GitHub Actions Run [39556894566](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/39556894566), commit `6db34503c1d6353076dc7db137ea204d89cc5953` (Win64 Rend2 3FX Visible V03). The Windows DLL cannot run on Android. This branch reconstructs the parent SOURCE, applies the existing GLES3 Android port, and attempts a native ARM64 build.

**Android donor:** Existing native Android TestLab branch `rend2-android-perf-testlab-v0.1`, whose emulator retail smoke passed in Run 37608794676. These scripts are copied by immutable Git blob SHA, not an unaudited binary.

**Do not call this an accepted Graphics Lab APK yet:** this initial CI gate validates source compatibility. The Lab overlay, command bridge, map chooser, native-resolution view and complete runtime CVar discovery must pass further gates and actual-device testing. No retail RTCW PK3 data is redistributed.

**Immutable defaults/guards:** `r_dlightmode=2`, `r_forceSun=1` must remain visible in a lab catalog and protected as canonical targets. Existing mobile-port startup defaults explicitly disable many effects; those defaults are *not* a faithful 3FX Graphics Lab preset.
