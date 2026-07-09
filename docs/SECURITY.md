# Security

MAIOS v1.0 is a local developer runtime with powerful extension points. Treat
tool execution, provider credentials, plugin loading, and autonomous execution as
trusted-environment capabilities.

## Supported Version

Security review applies to the active v1.0 line.

## Security-Sensitive Components

- `ShellTool` can execute shell commands.
- `PythonTool` can execute Python code or scripts.
- `FileTool` can read and write local files.
- `GitTool` can run Git commands.
- `PluginManager` can load Python modules from a plugin directory.
- `GPTAdapter` can call external LLM providers when configured.
- `AutonomousController` can execute missions without manual intervention in
  autonomous mode.

## Governance Controls

MAIOS includes a governance layer with:

- `PermissionModel`
- `PolicyEngine`
- risk classification
- high-risk approval gates
- JSON-backed `AuditLog`
- optional `GovernanceManager` integration with `AutonomousController`

Projects embedding MAIOS should configure policies for their environment before
enabling autonomous tool execution.

## Secrets

Do not commit:

- API keys
- access tokens
- credentials
- private documents
- generated sensitive outputs
- local audit logs containing sensitive data

Provider credentials should be supplied through environment variables.

## Reporting Security Issues

Report security concerns privately to the repository maintainer when possible.
If private reporting is not available, open a minimal public issue without
including exploit details, secrets, or sensitive runtime output.

Include:

- affected component
- impact summary
- reproduction outline
- suggested mitigation, if known

## Release Security Checklist

- Run the full quality gate.
- Review new tools, plugins, and provider integrations.
- Verify no generated `outputs/` artifacts are staged.
- Verify no secrets are committed.
- Review governance policy defaults.
