from aider.commands import Commands


def test_probe_001():
    # Target relative and absolute paths
    R = "docs/secret.md"
    A_rootsim = "/repo/docs/secret.md"
    A_readonly = "/readonly/docs/secret.md"

    # Minimal deterministic coder stub matching the activation conditions
    class DummyCoder:
        def get_all_relative_files(self):
            # Include the relative path R so it will be classified from get_all_relative_files()
            return [R, "other.txt"]

        def abs_root_path(self, rel):
            if rel == R:
                return A_rootsim
            return f"/repo/{rel}"

        # abs_fnames should NOT contain A_readonly so that the file is treated as a repo/non-chat file
        abs_fnames = {"/repo/other.txt"}

        # The read-only absolute name list contains a different absolute path that maps back to R
        abs_read_only_fnames = [A_readonly]

        def get_rel_fname(self, abs_path):
            if abs_path == A_readonly:
                return R
            # Fallback: return basename-like mapping for other inputs
            return abs_path

    # IO stub that captures tool_output calls in order
    class MockIO:
        def __init__(self):
            self.outputs = []

        def tool_output(self, text):
            # Capture exactly what the Commands implementation emits
            self.outputs.append(text)

    io = MockIO()
    coder = DummyCoder()

    # Create Commands using the public constructor and invoke the focused entrypoint
    commands = Commands(io, coder)
    commands.cmd_ls("")

    outputs = io.outputs

    repo_hdr = "Repo files not in the chat:\n"
    readonly_hdr = "\nRead-only files:\n"
    file_line = f"  {R}"

    # Primary behavioral oracle in one combined assertion:
    # - Both section headers are present
    # - The file line was printed
    # - The first occurrence of the file line is after the read-only header (i.e. not in the repo section)
    assert (
        repo_hdr in outputs
        and readonly_hdr in outputs
        and file_line in outputs
        and outputs.index(file_line) > outputs.index(readonly_hdr)
    ), (
        "Read-only exclusivity violated: expected 'docs/secret.md' to appear only under the Read-only files header "
        "and not in the 'Repo files not in the chat' section. Captured outputs: {}".format(outputs)
    )
