# Provenance v4.4.6

Baseline run 37266797451, builder e410db87b5704fb1518740f1cfc760e9ea67d34f, artifact 11326603946 verified through GitHub API. Downloaded archive SHA256 51a49587a0c4e7ad9c7ad651d5a4fcc34c7774d89ed9366dd659ed7efa97154b; inner ZIP 10ca3d568fdca89569912835d110fa9f365d531ec83982927fb5c1fe590f7aea. All internal SHA256SUMS entries verified locally.

Upstream 438e7d413b5f7277187c35b032eb0ef9093ae778. Builder branch starts at telemetry-kit 9378f655fa054b835b96989fa57efed9b3bf9585; its instrumentation is never applied to release source.

Critical reconstruction correction: historical v4.4.6 is assembled from separately built components. The telemetry workflow omits v4.4.3 AA, and does not reconstruct the UI. The new chain applies cumulative + seven verified shader donor additions + v4.4.3 AA + v4.4.4 sun + v4.4.5 cgame + v4.4.6 events/game + UI-only v4.4 + v4.4.2 UI. UI-only inclusion is deliberate: the cgame Tesla hunk in the UI delta was NOT used by v4.4.6's cgame rebuild and must not be reintroduced.

All patches and non-retail runtime payload are now versioned locally in the kit, eliminating historical artifact expiration as a build dependency. Gzip content and decompressed patch hashes, include filters, every baseline SP/code file, historical binary hashes and the reconstructed Git tree are in integration/optimized-v4-4-6/baseline_source_manifest.json. Git tree identity, rather than timestamp-dependent reconstructed commit ID, is the source identity.

The unified source is a component-correct reconstruction. Historical executable bit identity is NOT assumed: timestamps, toolchain and separately built modules can differ. The workflow separately rebuilds baseline and candidate with the same toolchain and requires unchanged EXE/cgame/qagame/UI hashes to agree between those rebuilds. Historical hashes remain in the comparison report for inspection.

Reconstructed baseline tree: `a9afb5a60e26eb112bc5a6af4bb52f4ed08685f1`.
