from aider.commands import Commands


class DummyModel:
    def __init__(self):
        # minimal model metadata used by cmd_tokens
        self.info = {"input_cost_per_token": 0, "max_input_tokens": 10000}
        self.name = "dummy"
        # capture every token_count invocation argument for later inspection
        self.captured = []

    def token_count(self, arg):
        # record the raw argument (could be a list for system/chat or a string for files)
        self.captured.append(arg)
        return 1

    def token_count_for_image(self, fname):
        # record image handling separately if invoked
        self.captured.append(("image", fname))
        return 2


class DummyCoder:
    def __init__(self, model):
        self.main_model = model
        # simple prompts used by fmt_system_prompt in cmd_tokens
        self.gpt_prompts = type("P", (), {"main_system": "MAIN", "system_reminder": "REM"})()
        self.done_messages = []
        self.cur_messages = []
        # single non-image absolute filename as required by the probe
        self.abs_fnames = ["/abs/path/file.txt"]
        # ensure read-only files branch is empty
        self.abs_read_only_fnames = []
        # repo_map falsy to avoid repo_map branch
        self.repo_map = None

    def choose_fence(self):
        # called by cmd_tokens; keep deterministic no-op
        return

    def fmt_system_prompt(self, s):
        return s

    def get_all_abs_files(self):
        # return the same set so other_files becomes empty
        return list(self.abs_fnames)

    def get_rel_fname(self, fname):
        # deterministic relative name used in the constructed content
        return "file.txt"


class DummyIO:
    def __init__(self, text):
        self._text = text
        self.outputs = []

    def read_text(self, fname):
        # return a non-empty body for the file
        return self._text

    def tool_output(self, *args, **kwargs):
        # record outputs but keep behavior minimal
        self.outputs.append(("out", args))

    def tool_error(self, *args, **kwargs):
        self.outputs.append(("err", args))


def test_generated_target_probe_asset_001():
    """
    Activation and primary oracle:
    - Activate cmd_tokens with a deterministic coder/io/model.
    - Inspect DummyModel.captured for the string argument corresponding to the non-image file.
    - Assert that this string ends with the closing fence sequence '\n```\n'.
    """
    model = DummyModel()
    coder = DummyCoder(model)
    io = DummyIO("file-body-line\n")

    # Construct Commands using the public entrypoint; this exercises Commands.cmd_tokens
    commands = Commands(io, coder)

    # Call the method under test; args are not required for this invocation path
    commands.cmd_tokens(None)

    # Find all captured token_count calls that are plain strings and include the relative filename
    str_calls = [c for c in model.captured if isinstance(c, str) and "file.txt" in c]

    # Primary behavioral assertion: there must be at least one file content call and it must include the closing fence
    assert len(str_calls) >= 1, "Expected at least one string argument containing the relative filename passed to token_count"

    # Choose the last such call (the file handling call should appear after system/chat calls)
    file_arg = str_calls[-1]

    # The expected invariant: content sent to the model for non-image files ends with a closing fence of three backticks
    assert file_arg.endswith("\n```\n"), (
        "The file content passed to main_model.token_count must end with a closing fence of three backticks (\\n```\\n). "
        f"Got: {file_arg!r}"
    )
