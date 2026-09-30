"""Reference checks for shared helpers used by both Python workflows."""

import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common.model_settings import message_content, parse_env_file


@pytest.fixture(params=["test_augmentF", "test_augment"])
def formal_client(request):
    root = os.environ.get("PROBE_FORMAL_ROOT")
    if not root:
        pytest.skip("set PROBE_FORMAL_ROOT for reference checks")
    import common

    directory = str(Path(root) / "src/common")
    if directory not in common.__path__:
        common.__path__.append(directory)
    return importlib.import_module(f"common.{request.param}.python.run.client")


def test_env_decoding_matches_both_clients(tmp_path, formal_client):
    source = tmp_path / "settings.env"
    assert parse_env_file(source) == formal_client.parse_env_file(source) == {}
    source.write_text(
        "# comment\nignored\nexport NAME = 'first'\nNAME=last=value\n"
        'QUOTED=" spaced "\nEMPTY=\n=blank-key\n'
    )
    assert parse_env_file(source) == formal_client.parse_env_file(source)


@pytest.mark.parametrize("content", ["", "plain", None, {"text": "value"}, ["part"]])
def test_message_decoding_matches_both_clients(formal_client, content):
    response = {"choices": [{"message": {"content": content}}]}
    assert message_content(response) == formal_client.message_content(response)
    assert message_content({}) == formal_client.message_content({}) == ""
