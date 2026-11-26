

\# DarkWolf RTCW — Engineering Instructions



\## Project



DarkWolf is an enhanced Return to Castle Wolfenstein

engine based on ioRTCW Rend2.



Primary target: Windows x86\_64.



\## Engineering goals



\- Preserve original RTCW gameplay.

\- Preserve campaign compatibility.

\- Preserve AI, scripting and game physics.

\- Improve rendering quality and performance.

\- Maintain compatibility with original game assets.

\- Avoid unnecessary architectural regressions.



\## Development rules



\- Inspect the repository before modifying code.

\- Identify the exact upstream source revision.

\- Inspect existing patches and integration scripts.

\- Reproduce the baseline before making changes.

\- Identify the root cause of each defect.

\- Prefer complete fixes over temporary workarounds.

\- Do not introduce unrelated changes.

\- Preserve backward compatibility where required.

\- Do not disable visual effects merely to hide defects.

\- Do not change existing default CVAR values

&#x20; without explicit authorization.



\## Renderer requirements



\- Preserve existing Rend2 functionality.

\- Validate GLSL changes in their actual engine context.

\- Check shader uniforms, defines and permutations.

\- Preserve HDR, Bloom, shadows and SSAO.

\- Preserve sunlight and fire volumetric lighting

&#x20; when modifying local lamp volumetric lighting.

\- Treat r\_volumetricLocalMode 5 as the existing

&#x20; local-lighting baseline unless instructed otherwise.

\- Investigate CPU and GPU performance separately.



\## Build requirements



\- Follow the repository's established build workflow.

\- Support Windows x64 builds.

\- Support native Linux checks where applicable.

\- Use MinGW-w64 for supported cross-compilation.

\- Use CMake and MSVC CI where required by the engine.

\- Limit parallel build jobs to available resources.

\- Never report a successful build without evidence.



\## Testing



\- Run applicable compilation and static checks.

\- Review changed shaders and affected render paths.

\- Check for regression risks.

\- Distinguish automated checks from in-game testing.

\- Do not claim visual validation without actual

&#x20; screenshots or verified rendering results.



\## Git workflow



\- Work on a dedicated development branch.

\- Do not force-push.

\- Do not overwrite stable release branches.

\- Do not delete existing releases or artifacts.

\- Do not expose credentials.

\- Document the exact commit and build configuration.



\## Release requirements



\- Prepare a complete Windows x64 ZIP package.

\- Include all required engine binaries and DLLs.

\- Preserve the required runtime directory structure.

\- Include required configuration files.

\- Exclude proprietary PK3 and PK4 game assets.

\- Include installation instructions.

\- Include a technical changelog.

\- Generate SHA256 checksums.

\- Verify the contents of the release archive.



\## Definition of done



A task is complete only when:



1\. The requested code changes are implemented.

2\. Applicable build and static checks have passed,

&#x20;  or failures are explicitly documented.

3\. Regression risks are documented.

4\. Changed files are listed.

5\. The exact source revision is recorded.

6\. Remaining in-game verification steps are identified.

7\. A release artifact is available if requested

&#x20;  and the environment supports its creation.



Never fabricate test results or release artifacts.



