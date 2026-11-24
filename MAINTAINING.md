# Maintaining and releasing

[julioromano/ha-daikin-home-hub on GitHub](https://github.com/julioromano/ha-daikin-home-hub) is the source of truth for code, issues, pull requests and releases. Use GitHub as `origin` and Forgejo as the release mirror.

## Architecture and dependencies

The protocol module consumes a `ModbusUnit` and owns no connection. Home Assistant owns shared TCP sockets and config-entry lifetime. Keep transport dependencies out of the runtime manifest. The checked-in development lock targets HA `2026.10.2` and its compatible backend versions; update them together in a focused compatibility change.

Register metadata drives HA descriptions and translations; explicit typed components define wire encodings. Model profiles apply manufacturer exclusions. The read planner restricts components to consecutive selected fields, adds enabled controls' limit dependencies, and isolates failed groups. Maintain these boundaries when adding features.

Installation options apply a field mask to polling and writes, and set entity defaults centrally. Toggled-off groups retain integration-disabled registry entries to preserve identifiers and customizations. Re-enabling clears only integration-owned disable states, never user/device/config-entry disable states. Model-incompatible fields retain the existing removal behavior. Entries without installation options keep the legacy policy until Configure is saved; do not infer commissioning from these stored choices.

Use current stable development tooling within the HA/Python constraints. Run formatting, linting, basedpyright, unit coverage, independent TCP tests and hassfest. HACS validation runs on GitHub pushes, pull requests, weekly and manual dispatch.

## GitHub settings

Enable issues and Actions. Use the description "Home Assistant integration for Daikin Home Hub Modbus TCP" and topics `home-assistant`, `hacs`, `daikin`, `homehub`, `modbus`.

Require up-to-date pull requests, squash merges and four passing GitHub Actions checks on `main`:

- **Lint, types and unit coverage**
- **Simulated Modbus TCP**
- **Home Assistant metadata**
- **HACS repository validation**

Reviews are optional and the bypass list is empty. Require linear history, block force pushes and branch deletion, and use read-only workflow permissions.

## Releases

1. Update the version in the project metadata, integration manifest and metadata test, and regenerate the lockfile when changing the version. Keep the HA minimum synchronized in the integration constants and HACS metadata.
2. Squash merge the version change through a pull request and wait for all four checks to pass on the resulting `main` commit.
3. Create an annotated `vVERSION` tag at that commit and push it to GitHub. Publish a GitHub Release using the standard source archive. Describe supported profiles, the manual revision, HA minimum, changes and limitations. Until hardware verification is recorded, describe all profiles as manufacturer-documented and simulator-tested.
4. Verify the released tag installs through HACS as a custom repository and Home Assistant can load it after restarting. Publish corrections as a new version.
5. After verification, atomically fast-forward `forgejo/main` to the released commit and push the same annotated tag. Confirm both refs match GitHub. Resolve any remote divergence or conflicting tag before retrying.

Unit coverage XML/HTML reports are uploaded even if tests fail. The minimum is 95% combined statement/branch coverage. TCP tests have a separate job without a line-coverage gate. Do not suppress HACS or hassfest checks to conceal metadata problems.

## Ongoing verification

Keep the [register inventory](docs/register-map.md), [manual index](docs/manuals.md), code and tests aligned. Record document revisions rather than inferring versions from upload-path dates. Recheck table footnotes and compatibility when firmware or manuals change.

Physical validation is pending for every profile. Use the README checklist and record actual equipment, commissioning and firmware per result. Avoid claiming an entire family was physically tested from one installation. Resolve manufacturer documentation gaps before adding other gateways, direct Altherma 4, EEBUS or PV-only use cases.
