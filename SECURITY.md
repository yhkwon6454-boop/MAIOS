# Security Policy

MAIOS v0.1 Alpha is an experimental local runtime. It includes tools that can
read files, write files, execute shell commands, execute Python code, and run Git
commands. These tools are powerful and should only be used in trusted
development environments.

## Supported Versions

Security review currently applies to the active v0.1 Alpha codebase.

## Important Security Notes

- `ShellTool` executes shell commands.
- `PythonTool` executes Python code or scripts.
- `FileTool` can read, write, append, and list files.
- `GitTool` can run Git commands.
- The reasoning engine can route model responses to registered tools.

Do not register tools for autonomous use unless the environment, inputs, and
permissions are trusted.

## Secrets

Do not commit secrets, API keys, tokens, credentials, private documents, or
generated sensitive outputs.

OpenAI credentials, when used, should be supplied through environment variables
such as `OPENAI_API_KEY`.

## Reporting Issues

For now, report security concerns through the repository issue tracker or
directly to the repository maintainer.

When reporting a security issue, include:

- Affected component.
- Reproduction steps.
- Expected impact.
- Suggested mitigation, if known.

## Current Limitations

MAIOS v0.1 Alpha does not yet implement:

- Tool permission policies.
- Human approval gates.
- Sandboxed command execution.
- Network access controls.
- Persistent audit logging.

These controls should be added before using MAIOS as an autonomous agent runtime.
