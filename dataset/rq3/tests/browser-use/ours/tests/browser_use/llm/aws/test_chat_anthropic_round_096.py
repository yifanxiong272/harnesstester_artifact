import pytest

from types import SimpleNamespace

from browser_use.llm.aws.chat_anthropic import ChatAnthropicBedrock


class _Creds:
    def __init__(self, access_key=None, secret_key=None, token=None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.token = token


class _SessionStub:
    def __init__(self, creds: _Creds, region_name: str | None):
        self._creds = creds
        self.region_name = region_name

    def get_credentials(self):
        return self._creds


def _make_instance():
    # Avoid running any real initializer on ChatAnthropicBedrock; create an instance
    # and set attributes directly to control all branches deterministically.
    inst = object.__new__(ChatAnthropicBedrock)
    return inst


def test_with_session_and_optionals_round_096():
    """Session path: session truthy -> credentials extracted; optionals included when truthy."""
    inst = _make_instance()

    # Provide a session with credentials and region
    creds = _Creds(access_key="AK_SESSION", secret_key="SK_SESSION", token="TK_SESSION")
    inst.session = _SessionStub(creds, region_name="us-west-2")

    # Make sure individual-credential attributes are irrelevant when session is present
    inst.aws_access_key = None
    inst.aws_secret_key = None
    inst.aws_region = None
    inst.aws_session_token = None

    # Optionals should be picked up when truthy
    inst.max_retries = 5
    inst.default_headers = {"h": "v"}
    inst.default_query = {"q": "1"}

    params = inst._get_client_params()

    expected = {
        "aws_access_key": "AK_SESSION",
        "aws_secret_key": "SK_SESSION",
        "aws_session_token": "TK_SESSION",
        "aws_region": "us-west-2",
        "max_retries": 5,
        "default_headers": {"h": "v"},
        "default_query": {"q": "1"},
    }

    # Exact dictionary equality ensures all branches for present optionals are covered
    assert params == expected


def test_no_session_all_individual_credentials_round_096():
    """No session path: individual credentials assigned -> those keys present; falsy optionals omitted."""
    inst = _make_instance()

    # Explicitly no session to hit the individual-credential branch
    inst.session = None

    # Provide all individual credentials
    inst.aws_access_key = "AK_IND"
    inst.aws_secret_key = "SK_IND"
    inst.aws_region = "eu-central-1"
    inst.aws_session_token = "TK_IND"

    # Optionals are falsy/None -> should not be present in result
    inst.max_retries = None
    inst.default_headers = None
    inst.default_query = None

    params = inst._get_client_params()

    expected = {
        "aws_access_key": "AK_IND",
        "aws_secret_key": "SK_IND",
        "aws_region": "eu-central-1",
        "aws_session_token": "TK_IND",
    }

    assert params == expected


def test_no_session_partial_credentials_round_096():
    """No session path with only one individual credential set -> ensure missing keys are omitted."""
    inst = _make_instance()
    inst.session = None

    # Only access key provided; others left falsy
    inst.aws_access_key = "AK_ONLY"
    inst.aws_secret_key = None
    inst.aws_region = None
    inst.aws_session_token = ""  # empty string should be falsy and thus omitted

    inst.max_retries = 0  # falsy
    inst.default_headers = {}
    inst.default_query = None

    params = inst._get_client_params()

    # Only aws_access_key should be present because other credential attributes are falsy
    assert params == {"aws_access_key": "AK_ONLY"}
