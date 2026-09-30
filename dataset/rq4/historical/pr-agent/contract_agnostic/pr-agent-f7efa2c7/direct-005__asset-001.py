def test_probe_001():
    from types import SimpleNamespace
    from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions

    # Prepare a dummy diff file where the relevant line (line 2) begins with a tab
    relevant_file = "some/file.py"
    # Line 1: no indent, Line 2: starts with a single tab
    head_file = "def func():\n\treturn 1\n"  # second line begins with a tab
    file_obj = SimpleNamespace(filename=relevant_file, head_file=head_file)

    # git_provider supplies diff_files; dedent_code will read self.git_provider.diff_files
    git_provider = SimpleNamespace(diff_files=[file_obj], get_diff_files=lambda: [file_obj])

    # Instantiate PRCodeSuggestions without running __init__ to avoid side effects
    instance = object.__new__(PRCodeSuggestions)
    instance.git_provider = git_provider

    # Suggestion's first line has no leading whitespace (so suggested_initial_spaces == 0)
    new_code_snippet = "return 2\nprint('x')\n"

    # Call the target entrypoint
    result = instance.dedent_code(relevant_file, 2, new_code_snippet)

    # Primary observable oracle: the first character of the returned first line should be a tab
    returned_first_line = result.splitlines()[0]
    assert returned_first_line, "Returned snippet first line is empty"
    assert returned_first_line[0] == '\t', (
        f"Expected the returned snippet's first line to start with a tab to preserve original indentation character, "
        f"but got: {repr(returned_first_line[:1])}. Full returned first line: {returned_first_line!r}"
    )
