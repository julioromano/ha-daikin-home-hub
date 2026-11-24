# Contributing

Keep changes scoped and reviewable. Report issues and open pull requests at [julioromano/ha-daikin-home-hub on GitHub](https://github.com/julioromano/ha-daikin-home-hub).

## Development

Use Python 3.14 and `uv`. Run `uv sync --frozen`, then the checks listed in the README. HA `2026.10.2` defines the compatible Modbus backend versions; runtime transport dependencies belong to HA, not this integration's manifest. Avoid new dependencies unless necessary.

Write a behavior-focused failing test before changing protocol behavior where practical. Keep independent reference fixtures separate from production register declarations. Exercise signed and scaled values, special markers, unknown values and error paths. Test changes at the HA entity-service boundary when they affect users.

Unit CI always publishes XML/HTML coverage and enforces the 95% combined statement/branch threshold. TCP tests run separately without a coverage gate, using an independent local server that rejects unsupported addresses and function codes. Preserve tests for all profiles, optional polling and shared-connection lifetime.

## Register and capability changes

Use manufacturer-hosted evidence. Record document number, revision, date and relevant page in the register reference/manual index. Check the rendered table, including merged type cells, footnotes, offset convention and use-case scope. Preserve different input/holding spaces and raw no-value markers.

Keep typed components, entity metadata, model applicability, translations, documentation and independent tests synchronized. Do not infer accessory presence from a zero value or expand support from a family name alone. Record specification-based support and hardware verification separately.

## Reporting a problem

Include the integration/HA versions, actual indoor/outdoor codes, selected compatibility profile and unit/HomeHub firmware. Download sanitized diagnostics and identify the affected register and expected unit-display value. Review diagnostics before sharing them, and include no credentials or unrelated personal information.

For control issues, describe commissioning, operating mode, schedules and the single action taken. Preserve the distinction between write acknowledgment, register readback and actual equipment operation. Do not repeatedly issue a command while investigating an ambiguous write failure.

## Review and release

Propose changes through a pull request and wait for all required checks before squash merging. Document user-visible changes and include them in the release notes. Follow [MAINTAINING.md](MAINTAINING.md) for repository settings and the release process.
