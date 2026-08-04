# CI trigger policy

The August 2026 CI-noise audit removed the copied `MLIP elastic-constant benchmark` workflow. This repository does not contain the canonical benchmark harness path referenced by that workflow, so every scheduled run failed before useful work began. The canonical manual diagnostic remains in `alexwelcing/lupine`; Rhizo must not carry a second schedule or a drifting copy.

The remaining triggers were retained: pull-request jobs validate repository-owned evidence and code, the repository-wide Verify workflow covers every main-branch push, narrower push jobs are path-filtered, scheduled evidence work owns Rhizo data, and production mutations are manual or explicitly gated. The MLIP discovery descriptor now points only to sources that remain in this repository.
