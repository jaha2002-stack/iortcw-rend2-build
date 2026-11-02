# Private RTCW retail assets for Renderer TestLab

The retail game files must never be committed to the public source repository.

## Private repository convention

- Repository: `jaha2002-stack/DarkWolfRTCW-TestAssets`
- Visibility: **Private**
- Release tag: `rtcw-retail-v1`

Release assets must be named exactly:

```
rtcw-assets.zip.part001
rtcw-assets.zip.part002
...
rtcw-assets.sha256
```

The number of parts is unrestricted by TestLab. The sequence must be contiguous.

## Build the multipart upload on Windows

Open PowerShell in a checkout of `iortcw-rend2-build` and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\testlab\scripts\split_rtcw_assets.ps1 -RtcwMainPath "C:\Path\To\Return to Castle Wolfenstein\Main"
```

The default part size is 500 MiB. To use another size:

```powershell
powershell -ExecutionPolicy Bypass -File .\testlab\scripts\split_rtcw_assets.ps1 -RtcwMainPath "C:\Path\To\RTCW\Main" -PartSizeMiB 400
```

Upload **every** generated file to the private release.

## Authentication used by the public TestLab workflow

Create a fine-grained GitHub personal access token that can read only the private
`DarkWolfRTCW-TestAssets` repository. Store it in the public
`jaha2002-stack/iortcw-rend2-build` repository as the Actions secret:

```
DARKWOLF_RTCW_ASSET_TOKEN
```

Do not paste the token into source, a release, an issue, or ChatGPT.

When the secret exists, TestLab downloads all parts from the private release,
checks that part numbers are contiguous, concatenates them, verifies the final
ZIP SHA-256 from `rtcw-assets.sha256`, extracts the PK3 files into the temporary
runner only, and executes the real map tests. Without the secret, runtime remains
explicitly gated as `BLOCKED_MISSING_RETAIL_ASSETS`.
