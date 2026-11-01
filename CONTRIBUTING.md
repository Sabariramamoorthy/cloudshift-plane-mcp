# Contributing

Thanks for helping improve CloudShift Plane MCP. Bug reports, compatibility notes for your Plane version, docs fixes, and pull requests are all welcome.

## Reporting a bug

Search [existing issues](https://github.com/Sabariramamoorthy/cloudshift-plane-mcp/issues) first, then [open a new one](https://github.com/Sabariramamoorthy/cloudshift-plane-mcp/issues/new/choose). Please include:

- Plane edition and version (Cloud, Commercial, or Community Edition `x.y.z`); the instance shows it at `/api/instances/`
- Transport (`stdio` or `http`) and MCP client (Cursor, Claude Desktop, …)
- The tool called, its arguments, and the error, with **API keys, workspace data, and hostnames removed**
- Output of `cloudshift_plane_capability_report` if the problem is a 404

Security issues go through [SECURITY.md](SECURITY.md), not public issues.

## Development setup

Requirements: Python 3.10+, [uv](https://docs.astral.sh/uv/), and for live tests, a Plane workspace you can safely write to.

```bash
git clone https://github.com/Sabariramamoorthy/cloudshift-plane-mcp.git
cd cloudshift-plane-mcp
uv sync --extra dev
uv run pytest
```

Unit tests need no network. The live integration test creates, updates, and deletes many resources, including **workspace-level** ones (customers, initiatives, relation definitions), and changes workspace feature flags. **Only point it at a throwaway workspace:**

```bash
cp .env.test .env.test.local      # fill in PLANE_TEST_* values
set -a; . ./.env.test.local; set +a
uv run plane-mcp-server http &    # in another terminal
uv run pytest tests/test_integration.py -v
```

## Making changes

1. Open an issue first for anything larger than a small fix, so we can agree on the approach.
2. Branch from `main`, keep the change focused, and add or update tests.
3. Before pushing:

   ```bash
   uv run ruff format .
   uv run ruff check .
   uv run pytest
   ```

4. Update the docs when behavior or configuration changes. If you add or rename tools, regenerate the list in [docs/tools.md](docs/tools.md).
5. Open a pull request using the template.

## Code guidelines

- Line length 120; ruff rules `E, F, I, UP, B`; Python 3.10+ syntax (`str | None`).
- **Upstream tools** (`plane_mcp/tools/`) follow the existing pattern: `@mcp.tool()`, typed parameters, a docstring with `Args` and `Returns` (MCP clients see it), and `plane-sdk` Pydantic return types. Keep changes there minimal so upstream merges stay easy.
- **Report tools** (`cloudshift/`) are read-only. Compute numbers in code, return the `ok()` / `CloudShiftError` envelope, and never guess: return `*_AMBIGUOUS` or `CAPABILITY_UNSUPPORTED` instead.
- Never log or return API keys. Use synthetic data in tests (see `tests/cloudshift/fixtures/`), never real workspace data.

## Upstream fixes

Fixes that aren't specific to this fork (for example a bug in an upstream tool) are often best sent to [makeplane/plane-mcp-server](https://github.com/makeplane/plane-mcp-server) as well, so everyone benefits.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
