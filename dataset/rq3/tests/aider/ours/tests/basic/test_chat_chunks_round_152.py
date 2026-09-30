from aider.coders.chat_chunks import ChatChunks


def test_examples_and_repo_present_round_152():
    # Use a lightweight dummy self to avoid requiring ChatChunks constructor
    calls = []

    class Dummy:
        pass

    d = Dummy()
    # examples truthy -> should call add_cache_control(self.examples)
    d.examples = ["example-message"]
    d.system = ["system-message"]
    # repo truthy -> should call add_cache_control(self.repo)
    d.repo = {"name": "repo"}
    # readonly_files should not be used when repo is truthy
    d.readonly_files = ["readonly1"]
    d.chat_files = ["chat1"]

    def recorder(arg):
        calls.append(arg)

    # Patch the instance method used by the function under test
    d.add_cache_control = recorder

    # Call the unbound function with our dummy instance to exercise branches
    ChatChunks.add_cache_control_headers(d)

    # Expectation: examples -> repo -> chat_files
    assert calls == [d.examples, d.repo, d.chat_files]


def test_no_examples_no_repo_round_152():
    # Another path: examples falsy -> system used; repo falsy -> readonly_files used
    calls = []

    class Dummy:
        pass

    d = Dummy()
    # empty list is falsy, so system should be used
    d.examples = []
    d.system = ["system-only"]
    # repo falsy -> readonly_files should be used
    d.repo = None
    d.readonly_files = ["readonly-only"]
    d.chat_files = ["chat-only"]

    def recorder(arg):
        calls.append(arg)

    d.add_cache_control = recorder

    ChatChunks.add_cache_control_headers(d)

    # Expectation: system -> readonly_files -> chat_files
    assert calls == [d.system, d.readonly_files, d.chat_files]
