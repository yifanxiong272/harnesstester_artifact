import pytest
from pathlib import Path

import browser_use.cli as cli


def test_list_templates_round_058(monkeypatch):
    # Prepare predictable templates mapping
    monkeypatch.setattr(cli, 'INIT_TEMPLATES', {
        'default': {'description': 'Default template', 'file': 'default.txt'},
        'advanced': {'description': 'Advanced template', 'file': 'advanced.txt'},
    })

    echoes = []

    def fake_echo(msg='', err=False, **kwargs):
        # record message and err flag
        echoes.append((str(msg), bool(err)))

    monkeypatch.setattr(cli.click, 'echo', fake_echo)

    # Call the underlying callback to avoid Click Context creation
    result = cli.init.callback(template=None, output=None, force=False, list_templates=True)

    assert result is None
    # First echo shows header
    assert any(msg == 'Available templates:\n' and not err for msg, err in echoes)
    # Subsequent echoes include the template descriptions formatted
    assert any('default' in msg and 'Default template' in msg for msg, _ in echoes)
    assert any('advanced' in msg and 'Advanced template' in msg for msg, _ in echoes)


def test_interactive_prompt_and_success_round_058(monkeypatch):
    # Simulate interactive selection when template not provided and output explicitly set
    monkeypatch.setattr(cli, 'INIT_TEMPLATES', {
        'advanced': {'description': 'Advanced description', 'file': 'advanced.tpl'},
    })

    # Capture prompt call and return a known template
    def fake_prompt(prompt_text, type=None, default=None):
        assert 'Which template' in prompt_text
        return 'advanced'

    monkeypatch.setattr(cli.click, 'prompt', fake_prompt)

    # Stub read_text on Path to return predictable content (no filesystem I/O)
    monkeypatch.setattr(cli.Path, 'read_text', lambda self, encoding='utf-8': 'TEMPLATE_CONTENT')

    # Track _write_init_file invocation and simulate successful write
    recorded = {}

    def fake_write_init_file(output_path, content, force):
        recorded['output_path'] = output_path
        recorded['content'] = content
        recorded['force'] = force
        return True

    monkeypatch.setattr(cli, '_write_init_file', fake_write_init_file)

    echoes = []
    monkeypatch.setattr(cli.click, 'echo', lambda msg='', err=False, **kwargs: echoes.append((str(msg), bool(err))))

    # Provide an explicit output filename to hit the output branch (Path(output))
    result = cli.init.callback(template=None, output='custom_out.py', force=False, list_templates=False)

    # Should return None and write function should have been called with provided output
    assert result is None
    assert 'output_path' in recorded
    assert recorded['output_path'].name == 'custom_out.py'
    assert recorded['content'] == 'TEMPLATE_CONTENT'
    assert recorded['force'] is False

    # Confirm CLI printed the created message
    assert any('Created' in msg and 'custom_out.py' in msg for msg, _ in echoes)
    # Confirm the next steps text is printed as well
    assert any('Next steps:' in msg for msg, _ in echoes)


def test_template_read_error_and_exit_round_058(monkeypatch):
    # Setup a template that will trigger a read error
    monkeypatch.setattr(cli, 'INIT_TEMPLATES', {
        'default': {'description': 'Default', 'file': 'does_not_matter.tpl'},
    })

    # Patch Path.read_text to raise an exception to hit the except branch
    def raise_on_read(self, encoding='utf-8'):
        raise RuntimeError('read failure')

    monkeypatch.setattr(cli.Path, 'read_text', raise_on_read)

    # Capture error echoes (err=True) and ensure sys.exit is invoked
    echoes = []

    def fake_echo(msg='', err=False, **kwargs):
        echoes.append((str(msg), bool(err)))

    monkeypatch.setattr(cli.click, 'echo', fake_echo)

    # Replace sys.exit with one that raises SystemExit so we can assert it
    monkeypatch.setattr(cli.sys, 'exit', lambda code=0: (_ for _ in ()).throw(SystemExit(code)))

    with pytest.raises(SystemExit) as excinfo:
        # Call underlying callback to avoid Click Context forwarding unexpected kwargs
        cli.init.callback(template='default', output=None, force=False, list_templates=False)

    # SystemExit should be raised with code 1 as per the except handler
    assert excinfo.value.code == 1
    # The error message should have been echoed with err=True
    assert any('Error reading template:' in msg and err for msg, err in echoes)
