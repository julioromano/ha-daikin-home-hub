# Maintaining and releasing

The distribution target is [julioromano/ha-daikin-home-hub](https://github.com/julioromano/ha-daikin-home-hub). Initial repository creation, remote changes and publication are separate from the implementation. The existing local remote is preserved.

## Architecture and dependencies

The protocol module consumes a `ModbusUnit` and owns no connection. Home Assistant owns shared TCP sockets and config-entry lifetime. Keep transport dependencies out of the runtime manifest. The checked-in development lock targets HA `2026.10.2` and its compatible backend versions; update them together in a focused compatibility change.

Register metadata drives HA descriptions and translations; explicit typed components define wire encodings. Model profiles apply manufacturer exclusions. The read planner restricts components to consecutive selected fields, adds enabled controls' limit dependencies, and isolates failed groups. Maintain these boundaries when adding features.

Installation options apply a field mask to polling and writes, and set entity defaults centrally. Toggled-off groups retain integration-disabled registry entries to preserve identifiers and customizations. Re-enabling clears only integration-owned disable states, never user/device/config-entry disable states. Model-incompatible fields retain the existing removal behavior. Entries without installation options keep the legacy policy until Configure is saved; do not infer commissioning from these stored choices.

Use current stable development tooling within the HA/Python constraints. Run formatting, linting, basedpyright, unit coverage, independent TCP tests and hassfest. HACS validation runs on GitHub pushes, pull requests, weekly and manual dispatch.

## GitHub setup after publication

Enable issues and Actions. Use the description "Home Assistant integration for Daikin Home Hub Modbus TCP" and topics `home-assistant`, `hacs`, `daikin`, `homehub`, `modbus`.

Protect `main` with reviewed pull requests and required checks: **Lint, types and unit coverage**, **Simulated Modbus TCP**, **Home Assistant metadata** and **HACS repository validation**. Prevent force pushes and branch deletion. Keep workflows read-only except where an explicit future publishing workflow requires more.

## Releases

1. Update matching versions in the project metadata and integration manifest; initial version is `0.1.0`. Keep the HA minimum synchronized in the integration constants and HACS metadata.
2. Run all checks and merge the version change through a reviewed pull request once publication is configured.
3. Create an annotated `vVERSION` tag from the tested commit and publish a GitHub Release. Tags/releases are immutable; corrections require a new version.
4. Describe supported profiles, manual revision, HA minimum, changes and limitations. Until hardware verification is recorded, describe all profiles as manufacturer-documented and simulator-tested.
5. Verify installation through a HACS custom repository. Use the ordinary `custom_components/daikin_home_hub` layout; no custom ZIP asset is required. HACS default-directory submission is a later step.

Unit coverage XML/HTML reports are uploaded even if tests fail. The minimum is 95% combined statement/branch coverage. TCP tests have a separate job without a line-coverage gate. Do not suppress HACS or hassfest checks to conceal metadata problems.

## Ongoing verification

Keep the [register inventory](docs/register-map.md), [manual index](docs/manuals.md), code and tests aligned. Record document revisions rather than inferring versions from upload-path dates. Recheck table footnotes and compatibility when firmware or manuals change.

Physical validation is pending for every profile. Use the README checklist and record actual equipment, commissioning and firmware per result. Avoid claiming an entire family was physically tested from one installation. Resolve manufacturer documentation gaps before adding other gateways, direct Altherma 4, EEBUS or PV-only use cases.
