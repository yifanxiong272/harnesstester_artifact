import pytest
from types import SimpleNamespace


def test_compose_yields_components_round_092(monkeypatch):
    """Exercise BrowserUseApp.compose and assert the sequence and payloads of yielded UI components.

    This test patches the symbols the compose method resolves so the generator can be executed
    deterministically without importing or running any real UI framework or filesystem calls.
    """
    # Import the module under test
    import browser_use.cli as cli

    # --- Lightweight test doubles ---
    class FakePath:
        def __init__(self, p="."):
            self._p = p

        def resolve(self):
            # Distinguish '.' from configured file path
            if self._p == ".":
                return FakePath("/current/dir")
            return FakePath(self._p)

        def __str__(self):
            return self._p

        @classmethod
        def home(cls):
            return FakePath("/home/user")

    class Header:
        def __repr__(self):
            return "<Header>"

    class Footer:
        def __repr__(self):
            return "<Footer>"

    class Container:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class HorizontalGroup(Container):
        pass

    class VerticalScroll(Container):
        pass

    class Static:
        def __init__(self, content="", **kwargs):
            self.content = content
            self.kwargs = kwargs

        def __repr__(self):
            return f"<Static {self.kwargs.get('id', '')}: {self.content!r}>"

    class Link:
        def __init__(self, text, url=None, **kwargs):
            self.text = text
            self.url = url
            self.kwargs = kwargs

        def __repr__(self):
            return f"<Link url={self.url!r}>"

    class RichLog:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __repr__(self):
            return f"<RichLog id={self.kwargs.get('id')!r}>"

    class Label:
        def __init__(self, text, **kwargs):
            self.text = text
            self.kwargs = kwargs

        def __repr__(self):
            return f"<Label {self.text!r}>"

    class Input:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __repr__(self):
            return f"<Input placeholder={self.kwargs.get('placeholder')!r}>"

    # --- Patch module-level symbols used by compose ---
    monkeypatch.setattr(cli, "Path", FakePath, raising=True)
    monkeypatch.setattr(cli, "Header", Header, raising=True)
    monkeypatch.setattr(cli, "Footer", Footer, raising=True)
    monkeypatch.setattr(cli, "Container", Container, raising=True)
    monkeypatch.setattr(cli, "HorizontalGroup", HorizontalGroup, raising=True)
    monkeypatch.setattr(cli, "VerticalScroll", VerticalScroll, raising=True)
    monkeypatch.setattr(cli, "Static", Static, raising=True)
    monkeypatch.setattr(cli, "Link", Link, raising=True)
    monkeypatch.setattr(cli, "RichLog", RichLog, raising=True)
    monkeypatch.setattr(cli, "Label", Label, raising=True)
    monkeypatch.setattr(cli, "Input", Input, raising=True)

    # Provide a deterministic BROWSER_LOGO and CONFIG for the f-string path formatting
    monkeypatch.setattr(cli, "BROWSER_LOGO", "<<LOGO>>", raising=True)
    monkeypatch.setattr(cli, "CONFIG", SimpleNamespace(BROWSER_USE_CONFIG_FILE=FakePath("/home/user/.browser-use")), raising=True)

    # Instantiate the app with a dict config (repair for prior failure) and collect yielded items
    app = cli.BrowserUseApp(config={})
    yielded = list(app.compose())

    # --- Assertions (observable behaviors) ---
    # 1) First: a Header instance is yielded
    assert any(isinstance(item, Header) for item in yielded), "Header not yielded"

    # 2) Logo Static exists with configured BROWSER_LOGO and id 'logo-panel'
    logo_statics = [s for s in yielded if isinstance(s, Static) and s.kwargs.get("id") == "logo-panel"]
    assert len(logo_statics) == 1, f"Expected one logo Static, got {logo_statics}"
    assert logo_statics[0].content == "<<LOGO>>"

    # 3) Links: verify presence and exact URLs for the link entries referenced in compose
    expected_urls = {
        "https://browser-use.com?utm_source=oss&utm_medium=cli",
        "https://discord.gg/ESAUZAdxXY",
        "https://github.com/browser-use/awesome-prompts",
        "https://github.com/browser-use/browser-use/issues",
    }
    found_urls = {l.url for l in yielded if isinstance(l, Link)}
    assert expected_urls.issubset(found_urls), f"Missing expected link URLs. Found: {found_urls}"

    # 4) There is an empty Static used as a spacer ('' content)
    assert any(isinstance(s, Static) and s.content == "" for s in yielded), "Empty spacer Static not yielded"

    # 5) Paths panel Static contains the 'Settings saved to' and uses '~' for home replacement
    paths = [s for s in yielded if isinstance(s, Static) and s.kwargs.get("id") == "paths-panel"]
    assert len(paths) == 1, "paths-panel Static missing"
    paths_text = paths[0].content
    assert "Settings saved to:" in paths_text
    assert "Outputs & recordings saved to:" in paths_text
    # Home should be folded to '~' because FakePath.home() -> '/home/user' and replace occurs in compose
    assert "~" in paths_text
    # Current directory resolved value provided by FakePath.resolve for '.' should appear
    assert "/current/dir" in paths_text

    # 6) RichLog ids exist for browser, model, tasks and three-column logs
    ids = {r.kwargs.get("id") for r in yielded if isinstance(r, RichLog)}
    for required in ("browser-info", "model-info", "tasks-info", "main-output-log", "events-log", "cdp-log"):
        assert required in ids, f"RichLog with id {required} not yielded"

    # 7) tasks-info and main-output-log were created with auto_scroll=True
    def find_richlog(id_):
        for r in yielded:
            if isinstance(r, RichLog) and r.kwargs.get("id") == id_:
                return r
        return None

    tasks_log = find_richlog("tasks-info")
    assert tasks_log is not None and tasks_log.kwargs.get("auto_scroll") is True
    main_output_log = find_richlog("main-output-log")
    assert main_output_log is not None and main_output_log.kwargs.get("auto_scroll") is True

    # 8) Task input label and input placeholder
    labels = [l for l in yielded if isinstance(l, Label)]
    assert any("What would you like me to do on the web?" in lbl.text for lbl in labels), "Task label text missing"
    inputs = [i for i in yielded if isinstance(i, Input)]
    assert any(i.kwargs.get("placeholder") == "Enter your task..." for i in inputs), "Input placeholder mismatch"

    # 9) Final yielded component is Footer (as the compose yields Footer() at the end)
    assert isinstance(yielded[-1], Footer), f"Expected final yield to be Footer but got {yielded[-1]!r}"
