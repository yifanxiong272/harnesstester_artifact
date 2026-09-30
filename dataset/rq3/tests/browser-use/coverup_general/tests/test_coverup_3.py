# file: browser_use/browser/watchdogs/default_action_watchdog.py:702-1060
# asked: {"lines": [710, 712, 713, 715, 716, 718, 720, 721, 723, 726, 729, 732, 735, 736, 737, 738, 739, 740, 741, 743, 744, 745, 746, 747, 748, 749, 750, 751, 753, 755, 756, 757, 758, 761, 762, 763, 766, 767, 768, 770, 771, 772, 773, 776, 779, 780, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 795, 796, 800, 801, 802, 803, 804, 805, 807, 808, 810, 812, 813, 814, 815, 817, 819, 821, 822, 823, 824, 825, 827, 830, 831, 833, 834, 835, 838, 839, 840, 841, 844, 845, 848, 849, 850, 851, 853, 854, 855, 857, 858, 859, 861, 863, 864, 867, 868, 871, 872, 875, 877, 878, 879, 880, 881, 882, 884, 885, 887, 889, 890, 891, 892, 894, 896, 897, 898, 899, 900, 903, 904, 906, 907, 908, 909, 910, 912, 914, 917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 928, 930, 932, 933, 934, 938, 939, 940, 941, 942, 943, 944, 945, 946, 948, 950, 952, 953, 955, 958, 959, 960, 961, 962, 963, 964, 965, 967, 969, 970, 972, 973, 975, 976, 977, 979, 980, 981, 982, 983, 984, 986, 988, 989, 990, 991, 992, 995, 997, 998, 1000, 1001, 1002, 1003, 1005, 1006, 1008, 1010, 1011, 1012, 1013, 1015, 1019, 1021, 1022, 1023, 1024, 1028, 1029, 1030, 1031, 1032, 1034, 1035, 1036, 1037, 1039, 1040, 1041, 1042, 1043, 1045, 1046, 1047, 1048, 1051, 1054, 1055, 1057, 1058, 1059], "branches": [[715, 716], [715, 720], [720, 721], [720, 726], [738, 739], [738, 761], [745, 746], [745, 747], [780, 782], [780, 800], [800, 801], [800, 830], [824, 825], [824, 827], [833, 834], [833, 861], [834, 835], [834, 838], [844, 845], [844, 848], [857, 833], [857, 858], [861, 863], [861, 867], [877, 878], [877, 903], [958, 959], [958, 995], [970, 972], [970, 989], [1046, 1047], [1046, 1048], [1054, 1055], [1054, 1057]]}
# gained: {"lines": [710, 712, 713, 715, 716, 718, 720, 721, 723, 726, 729, 732, 735, 736, 737, 738, 739, 740, 741, 743, 744, 745, 747, 748, 749, 750, 751, 753, 755, 756, 761, 762, 763, 766, 767, 768, 770, 771, 776, 779, 780, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 795, 796, 800, 801, 802, 803, 804, 805, 807, 810, 812, 813, 814, 815, 817, 819, 821, 830, 831, 833, 834, 838, 839, 840, 841, 844, 848, 849, 850, 851, 853, 854, 855, 857, 858, 859, 861, 867, 868, 871, 872, 875, 877, 903, 904, 906, 907, 908, 909, 910, 912, 914, 917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 928, 930, 933, 934, 938, 939, 940, 941, 942, 943, 944, 945, 946, 948, 950, 952, 953, 955, 958, 959, 960, 961, 962, 963, 964, 965, 967, 969, 970, 972, 973, 975, 976, 977, 979, 980, 981, 982, 983, 984, 986, 988, 989, 990, 1028, 1029, 1030, 1031, 1032, 1039, 1041, 1043, 1045, 1046, 1047, 1048, 1051, 1054, 1055, 1057, 1058, 1059], "branches": [[715, 716], [715, 720], [720, 721], [720, 726], [738, 739], [738, 761], [745, 747], [780, 782], [780, 800], [800, 801], [800, 830], [833, 834], [833, 861], [834, 838], [844, 848], [857, 858], [861, 867], [877, 903], [958, 959], [970, 972], [1046, 1047], [1054, 1055]]}

import asyncio
import types
import pytest

from browser_use.browser.views import BrowserError
from browser_use.browser.watchdogs.default_action_watchdog import DefaultActionWatchdog


class DummyLogger:
    def debug(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class SimpleRect:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class FakeSend:
    def __init__(self, parent):
        self._p = parent
        self.DOM = types.SimpleNamespace(
            resolveNode=self._dom_resolve_node,
            scrollIntoViewIfNeeded=self._dom_scroll_into_view_if_needed,
        )
        self.Runtime = types.SimpleNamespace(
            callFunctionOn=self._runtime_call_function_on,
            runIfWaitingForDebugger=self._runtime_run_if_waiting_for_debugger,
        )
        self.Page = types.SimpleNamespace(
            getLayoutMetrics=self._page_get_layout_metrics,
        )
        self.Input = types.SimpleNamespace(
            dispatchMouseEvent=self._input_dispatch_mouse_event,
        )

    async def _dom_resolve_node(self, params=None, session_id=None):
        if 'raise_resolve' in self._p.flags:
            raise Exception(self._p.flags['raise_resolve'])
        return {'object': {'objectId': self._p.flags.get('objectId', 'obj1')}}

    async def _dom_scroll_into_view_if_needed(self, params=None, session_id=None):
        if self._p.flags.get('scroll_raises'):
            raise Exception('scroll failed')
        return {}

    async def _runtime_call_function_on(self, params=None, session_id=None):
        fd = (params or {}).get('functionDeclaration', '')
        if not hasattr(self._p, 'call_seq'):
            self._p.call_seq = []
        self._p.call_seq.append(fd)
        if 'return this.checked' in fd or 'return this.checked;' in fd:
            if self._p.flags.get('checked_values'):
                return {'result': {'value': self._p.flags['checked_values'].pop(0)}}
            return {'result': {'value': self._p.flags.get('checked_default', False)}}
        if 'this.click' in fd:
            return {}
        return {}

    async def _runtime_run_if_waiting_for_debugger(self, session_id=None):
        if self._p.flags.get('run_if_waiting_raises'):
            raise Exception('run if waiting failed')
        return {}

    async def _page_get_layout_metrics(self, session_id=None):
        return {'layoutViewport': {'clientWidth': self._p.flags.get('viewport_width', 800),
                                   'clientHeight': self._p.flags.get('viewport_height', 600)}}

    async def _input_dispatch_mouse_event(self, params=None, session_id=None):
        typ = (params or {}).get('type')
        if typ == 'mousePressed' and self._p.flags.get('mousePressed_raises'):
            raise TimeoutError('mouse pressed timeout')
        if typ == 'mouseReleased' and self._p.flags.get('mouseReleased_raises'):
            raise TimeoutError('mouse released timeout')
        return {}


class FakeCDPSession:
    def __init__(self, parent):
        self.session_id = parent.flags.get('session_id', 'S1')
        send = FakeSend(parent)
        send._p = parent
        self.cdp_client = types.SimpleNamespace(send=send)


class FakeBrowserSession:
    def __init__(self):
        self.flags = {}
        self.call_seq = []

    async def cdp_client_for_node(self, element_node):
        sess = FakeCDPSession(self)
        sess.cdp_client.send._p = self
        return sess

    async def get_element_coordinates(self, backend_node_id, cdp_session):
        rect = self.flags.get('rect')
        if rect is None:
            return None
        return SimpleRect(*rect)

    async def get_or_create_cdp_session(self, focus=False):
        sess = FakeCDPSession(self)
        sess.cdp_client.send._p = self
        return sess


class DummyElementNode:
    def __init__(self, tag_name=None, attributes=None, backend_node_id=None):
        self.tag_name = tag_name
        self.attributes = attributes or {}
        self.backend_node_id = backend_node_id


async def _bind_and_run_click_impl(browser_session, element_node, logger=None, extra_attrs=None):
    # Create a fake self object and bind the class function to it
    fake_self = types.SimpleNamespace()
    fake_self.browser_session = browser_session
    fake_self.logger = logger or DummyLogger()
    # Attach any extra attributes (like overrides)
    if extra_attrs:
        for k, v in extra_attrs.items():
            setattr(fake_self, k, v)
    # Bind the function and call it
    func = DefaultActionWatchdog._click_element_node_impl
    bound = types.MethodType(func, fake_self)
    return await bound(element_node)


@pytest.mark.asyncio
async def test_select_and_file_input_returns_validation_error():
    bs = FakeBrowserSession()
    select_node = DummyElementNode(tag_name='select', attributes={}, backend_node_id=123)
    file_node = DummyElementNode(tag_name='input', attributes={'type': 'file'}, backend_node_id=456)

    res_select = await _bind_and_run_click_impl(bs, select_node)
    assert isinstance(res_select, dict)
    assert 'validation_error' in res_select
    assert 'Cannot click on <select' in res_select['validation_error']

    res_file = await _bind_and_run_click_impl(bs, file_node)
    assert isinstance(res_file, dict)
    assert 'validation_error' in res_file
    assert 'Cannot click on file input element' in res_file['validation_error']


@pytest.mark.asyncio
async def test_js_fallback_when_no_geometry_calls_runtime_click_and_returns_none():
    bs = FakeBrowserSession()
    bs.flags['rect'] = None
    bs.flags['objectId'] = 'obj_js'

    node = DummyElementNode(tag_name='div', attributes={}, backend_node_id=1)

    res = await _bind_and_run_click_impl(bs, node)
    assert res is None
    # Ensure that runtime click was attempted (call_seq should contain a functionDeclaration with click)
    assert any('this.click' in (s or '') for s in bs.call_seq)


@pytest.mark.asyncio
async def test_checkbox_click_uses_mouse_then_js_fallback_and_returns_checked_state():
    bs = FakeBrowserSession()
    bs.flags['rect'] = (10, 20, 30, 40)
    bs.flags['viewport_width'] = 800
    bs.flags['viewport_height'] = 600
    bs.flags['checked_values'] = [True, True, False]
    bs.flags['objectId'] = 'checkbox_obj'
    bs.flags['mousePressed_raises'] = True
    bs.flags['mouseReleased_raises'] = True

    async def fake_check_occlusion(backend_node_id, x, y, cdp_session):
        return False

    node = DummyElementNode(tag_name='input', attributes={'type': 'checkbox'}, backend_node_id=77)

    res = await _bind_and_run_click_impl(bs, node, extra_attrs={'_check_element_occlusion': fake_check_occlusion})
    assert isinstance(res, dict)
    assert 'click_x' in res and 'click_y' in res
    assert res.get('checked') is False


@pytest.mark.asyncio
async def test_general_exception_wraps_in_browser_error_with_long_term_memory():
    bs = FakeBrowserSession()

    async def raise_cdp_client_for_node(element_node):
        raise Exception("boom")

    bs.cdp_client_for_node = raise_cdp_client_for_node

    node = DummyElementNode(tag_name='button', attributes={}, backend_node_id=999)

    with pytest.raises(BrowserError) as ei:
        await _bind_and_run_click_impl(bs, node)

    be = ei.value
    assert isinstance(be, BrowserError)
    assert 'index=999' in getattr(be, 'long_term_memory', '') or '999' in getattr(be, 'long_term_memory', '')
