def test_generated_target_probe_asset_004():
    from aider.coders.editblock_func_coder import EditBlockFunctionCoder
    import aider.coders.editblock_func_coder as mod

    inst = object.__new__(EditBlockFunctionCoder)
    inst.partial_response_function_call = {"name": "replace_lines"}

    # One edit that will 'fail' when do_replace is called
    inst.parse_partial_args = lambda: {
        "edits": [
            {"path": "fail.py", "original_lines": ["x"], "updated_lines": ["y"]}
        ]
    }

    inst.code_format = "string"
    inst.allowed_to_edit = lambda p: f"/abs/{p}"
    inst.dry_run = False

    class DummyIO:
        def __init__(self):
            self.messages = []
        def tool_error(self, m):
            self.messages.append(m)

    inst.io = DummyIO()

    # get_arg basic extractor
    mod.get_arg = lambda edit, key: edit.get(key)

    # Simulate failing replacement
    def do_replace_fail(full_path, original, updated, dry_run):
        return False

    mod.do_replace = do_replace_fail

    result = inst.update_files()

    # The io should have recorded the failure message and the edited set must not include the path
    assert any("fail.py" in m for m in inst.io.messages)
    assert (result is None) or ("fail.py" not in result)
