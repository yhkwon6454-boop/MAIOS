from maios.tools import (
    BaseTool,
    FileTool,
    GitTool,
    PythonTool,
    ShellTool,
    ToolRegistry,
    ToolResult,
)


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo test input."

    def execute(self, input_data):
        return ToolResult(success=True, output=input_data["value"])


def test_tool_registry_register_get_execute_and_unregister():
    registry = ToolRegistry()
    tool = EchoTool()

    registry.register(tool)

    assert registry.exists("echo")
    assert registry.get("echo") is tool
    assert registry.names() == ["echo"]
    assert registry.execute("echo", {"value": "ok"}).output == "ok"

    registry.unregister("echo")

    assert not registry.exists("echo")


def test_tool_registry_unknown_tool_returns_failure():
    result = ToolRegistry().execute("missing", {})

    assert not result.success
    assert result.error == "Tool not found: missing"
    assert result.metadata["tool"] == "missing"


def test_tool_registry_requires_tool_name():
    class NamelessTool(BaseTool):
        name = ""

        def execute(self, input_data):
            return ToolResult(success=True)

    registry = ToolRegistry()

    try:
        registry.register(NamelessTool())
    except ValueError as exc:
        assert str(exc) == "Tool name is required."
    else:
        raise AssertionError("Expected ValueError for nameless tool.")


def test_file_tool_write_read_append_exists_and_list(tmp_path):
    tool = FileTool(root=tmp_path)

    write_result = tool.execute(
        {"action": "write", "path": "notes/task.txt", "content": "alpha"}
    )
    append_result = tool.execute(
        {"action": "append", "path": "notes/task.txt", "content": "\nbeta"}
    )
    read_result = tool.execute({"action": "read", "path": "notes/task.txt"})
    exists_result = tool.execute({"action": "exists", "path": "notes/task.txt"})
    list_result = tool.execute({"action": "list", "path": "notes"})

    assert write_result.success
    assert append_result.success
    assert read_result.output == "alpha\nbeta"
    assert exists_result.metadata["exists"] is True
    assert list_result.metadata["items"] == ["task.txt"]


def test_file_tool_blocks_paths_outside_root(tmp_path):
    tool = FileTool(root=tmp_path)
    outside_path = tmp_path.parent / "outside.txt"

    result = tool.execute({"action": "read", "path": outside_path})

    assert not result.success
    assert "Path is outside root" in result.error


def test_file_tool_rejects_unknown_action(tmp_path):
    result = FileTool(root=tmp_path).execute({"action": "delete", "path": "x"})

    assert not result.success
    assert result.error == "Unsupported file action: delete"


def test_python_tool_executes_inline_code():
    result = PythonTool().execute({"code": "print(2 + 3)"})

    assert result.success
    assert result.output.strip() == "5"
    assert result.metadata["returncode"] == 0


def test_python_tool_reports_script_errors():
    result = PythonTool().execute({"code": "raise SystemExit(7)"})

    assert not result.success
    assert result.metadata["returncode"] == 7


def test_shell_tool_executes_command():
    result = ShellTool().execute({"command": "echo maios"})

    assert result.success
    assert "maios" in result.output
    assert result.metadata["returncode"] == 0


def test_shell_tool_requires_command():
    result = ShellTool().execute({})

    assert not result.success
    assert result.error == "Shell command is required."


def test_git_tool_executes_git_status():
    result = GitTool(repo_path=".").execute({"args": ["status", "--short"]})

    assert result.success
    assert result.metadata["command"] == ["git", "status", "--short"]


def test_git_tool_requires_args():
    result = GitTool().execute({})

    assert not result.success
    assert result.error == "Git args are required."
