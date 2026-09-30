import pytest
from browser_use.cli import update_config_with_click_args


class DummyCtx:
    def __init__(self, params: dict):
        # click.Context has an attribute `params` used as a mapping in the function
        self.params = params


def test_update_config_sets_all_fields_round_047():
    # start with no model/browser sections to hit creation branches (lines ~307-311)
    config = {}
    params = {
        'model': 'gpt-test',
        'headless': True,
        'window_width': 1280,
        'window_height': 720,
        'user_data_dir': '/tmp/userdata',
        'profile_directory': 'Profile 1',
        'cdp_url': 'http://localhost:9222'
    }
    ctx = DummyCtx(params)

    out = update_config_with_click_args(config, ctx)

    # function returns the same (possibly mutated) dict
    assert out is config

    # model section created and name set
    assert 'model' in out
    assert out['model']['name'] == 'gpt-test'

    # browser section created and fields set
    assert 'browser' in out
    browser = out['browser']
    assert browser['headless'] is True
    assert browser['window_width'] == 1280
    assert browser['window_height'] == 720
    assert browser['user_data_dir'] == '/tmp/userdata'
    assert browser['profile_directory'] == 'Profile 1'
    assert browser['cdp_url'] == 'http://localhost:9222'


def test_update_config_proxy_round_047():
    # Test proxy dict assembly and no_proxy normalization (line ~329-340)
    config = {}
    params = {
        'proxy_url': 'http://proxy.example:8080',
        # include spaces, empty segments, and surrounding commas to exercise join/filter
        'no_proxy': ' localhost, , 127.0.0.1 , ,example.com ',
        'proxy_username': 'proxyuser',
        'proxy_password': 'proxypass'
    }
    ctx = DummyCtx(params)

    out = update_config_with_click_args(config, ctx)

    assert 'browser' in out
    proxy = out['browser'].get('proxy')
    assert isinstance(proxy, dict)

    # server should be passed through unchanged
    assert proxy['server'] == 'http://proxy.example:8080'

    # bypass should be a comma-separated list, trimmed and without empty entries
    # expected order preserved from input after trimming/filtering
    assert proxy['bypass'] == 'localhost,127.0.0.1,example.com'

    # username/password should be copied
    assert proxy['username'] == 'proxyuser'
    assert proxy['password'] == 'proxypass'


def test_update_config_headless_false_and_no_proxy_round_047():
    # Ensure explicit False for headless is preserved (branch: get('headless') is not None)
    # and that when proxy is empty it is not added to browser (proxy dict falsy)
    config = {}
    params = {
        'headless': False
        # no proxy_* keys provided -> proxy should remain absent
    }
    ctx = DummyCtx(params)

    out = update_config_with_click_args(config, ctx)

    assert 'browser' in out
    assert out['browser']['headless'] is False
    # proxy should not be present when no proxy fields were provided
    assert 'proxy' not in out['browser']
