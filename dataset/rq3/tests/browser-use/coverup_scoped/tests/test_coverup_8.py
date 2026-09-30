# file: browser_use/browser/session.py:3604-3743
# asked: {"lines": [3612, 3613, 3616, 3619, 3620, 3621, 3622, 3623, 3624, 3625, 3626, 3627, 3629, 3632, 3633, 3636, 3637, 3640, 3642, 3643, 3645, 3646, 3647, 3648, 3651, 3652, 3653, 3654, 3656, 3657, 3659, 3661, 3664, 3666, 3667, 3669, 3672, 3675, 3676, 3677, 3678, 3679, 3680, 3681, 3682, 3683, 3684, 3685, 3686, 3687, 3688, 3689, 3690, 3695, 3696, 3697, 3700, 3701, 3704, 3705, 3708, 3709, 3710, 3711, 3712, 3713, 3716, 3718, 3720, 3721, 3722, 3724, 3727, 3728, 3729, 3732, 3734, 3736, 3740, 3741, 3743], "branches": [[3632, 3633], [3632, 3740], [3636, 3637], [3636, 3640], [3640, 3642], [3640, 3651], [3642, 3643], [3642, 3645], [3656, 3632], [3656, 3657], [3669, 0], [3669, 3672], [3696, 3697], [3696, 3700], [3700, 3701], [3700, 3704], [3704, 3705], [3704, 3708], [3709, 3710], [3709, 3716], [3712, 3709], [3712, 3713], [3716, 3718], [3716, 3724], [3720, 3721], [3720, 3727], [3727, 0], [3727, 3728], [3728, 0], [3728, 3729], [3740, 3741], [3740, 3743]]}
# gained: {"lines": [3612, 3613, 3616, 3619, 3620, 3621, 3622, 3623, 3624, 3625, 3626, 3627, 3629, 3632, 3633, 3636, 3637, 3640, 3642, 3643, 3645, 3646, 3647, 3648, 3651, 3652, 3656, 3657, 3659, 3661, 3664, 3666, 3667, 3669, 3672, 3675, 3676, 3677, 3678, 3679, 3680, 3681, 3682, 3683, 3684, 3685, 3686, 3687, 3688, 3689, 3690, 3695, 3696, 3697, 3700, 3701, 3704, 3705, 3708, 3709, 3710, 3711, 3712, 3713, 3716, 3718, 3720, 3721, 3722, 3724, 3727, 3728, 3729, 3732, 3734, 3736, 3740, 3741, 3743], "branches": [[3632, 3633], [3632, 3740], [3636, 3637], [3636, 3640], [3640, 3642], [3640, 3651], [3642, 3643], [3642, 3645], [3656, 3657], [3669, 3672], [3696, 3697], [3696, 3700], [3700, 3701], [3700, 3704], [3704, 3705], [3704, 3708], [3709, 3710], [3709, 3716], [3712, 3713], [3716, 3718], [3716, 3724], [3720, 3721], [3727, 3728], [3728, 0], [3728, 3729], [3740, 3741], [3740, 3743]]}

import pytest
import asyncio
from types import SimpleNamespace

from browser_use.browser.session import BrowserSession
from browser_use.browser.profile import BrowserProfile


class FakeCDPSend:
    def __init__(self, get_frame_tree_coro):
        # store coroutine function
        self.Page = SimpleNamespace(getFrameTree=get_frame_tree_coro)


class FakeCDPSession:
    def __init__(self, session_id, get_frame_tree_coro):
        self.session_id = session_id
        self.cdp_client = SimpleNamespace(send=FakeCDPSend(get_frame_tree_coro))


@pytest.mark.asyncio
async def test_get_all_frames_with_cross_origin_and_merging(monkeypatch):
    """
    Test include_cross_origin = True:
    - multiple targets (page + iframe + one that raises)
    - proper frame tree processing
    - merging when same frame appears on iframe target (sets frameTargetId and isCrossOrigin)
    - _populate_frame_metadata is called with the collected frames and target_sessions
    """
    # Prepare session with cross_origin_iframes enabled
    session = BrowserSession(browser_profile=BrowserProfile(cross_origin_iframes=True))

    # Targets: page t1, iframe t2, page t3 (will have getFrameTree raise)
    targets = [
        {'targetId': 't1', 'type': 'page'},
        {'targetId': 't2', 'type': 'iframe'},
        {'targetId': 't3', 'type': 'page'},
    ]

    async def fake_cdp_get_all_pages(self, *args, **kwargs):
        return targets

    monkeypatch.setattr(BrowserSession, "_cdp_get_all_pages", fake_cdp_get_all_pages, raising=True)

    # Prepare frame trees for t1 and t2
    async def get_frame_tree_t1(session_id=None):
        # f1 has child f2
        return {
            'frameTree': {
                'frame': {'id': 'f1', 'url': 'https://example.com'},
                'childFrames': [
                    {'frame': {'id': 'f2', 'url': 'https://child.example.com'}},
                ],
            }
        }

    async def get_frame_tree_t2(session_id=None):
        # iframe target provides f2 as a top-level frame belonging to t2 and declares parentId -> f1
        return {
            'frameTree': {
                'frame': {'id': 'f2', 'url': 'https://child.example.com', 'parentId': 'f1'},
                'childFrames': [],
            }
        }

    async def get_frame_tree_t3(session_id=None):
        raise RuntimeError("no frames for t3")

    # get_or_create_cdp_session returns different fake sessions depending on target id
    async def fake_get_or_create_cdp_session(self, target_id, focus=False):
        if target_id == 't1':
            return FakeCDPSession('s1', get_frame_tree_t1)
        if target_id == 't2':
            return FakeCDPSession('s2', get_frame_tree_t2)
        if target_id == 't3':
            # Return a session whose getFrameTree will raise to trigger the exception-handling branch
            return FakeCDPSession('s3', get_frame_tree_t3)
        raise ValueError("unknown target")

    monkeypatch.setattr(BrowserSession, "get_or_create_cdp_session", fake_get_or_create_cdp_session, raising=True)

    # Track calls to _populate_frame_metadata
    called = {}

    async def fake_populate_frame_metadata(self, all_frames, target_sessions):
        called['all_frames'] = dict(all_frames)  # copy snapshot
        called['target_sessions'] = dict(target_sessions)

    monkeypatch.setattr(BrowserSession, "_populate_frame_metadata", fake_populate_frame_metadata, raising=True)

    all_frames, target_sessions = await session.get_all_frames()

    # Assertions:
    # - both frames f1 and f2 should be present
    assert 'f1' in all_frames
    assert 'f2' in all_frames

    f1 = all_frames['f1']
    f2 = all_frames['f2']

    # f1 should list f2 as child
    assert 'f2' in f1.get('childFrameIds', [])

    # After merging, f2 should have been assigned frameTargetId 't2' (iframe) and marked isCrossOrigin True
    assert f2.get('frameTargetId') == 't2'
    assert f2.get('isCrossOrigin') is True

    # target_sessions should include t1,t2,t3 mapping to session ids
    assert target_sessions == {'t1': 's1', 't2': 's2', 't3': 's3'}

    # _populate_frame_metadata should have been called (because cross-origin support enabled)
    assert 'all_frames' in called
    # snapshots should match returned dict
    assert called['all_frames'] == all_frames
    assert called['target_sessions'] == target_sessions


@pytest.mark.asyncio
async def test_get_all_frames_without_cross_origin_focus_missing_session(monkeypatch):
    """
    Test include_cross_origin = False:
    - agent_focus_target_id set, but get_or_create_cdp_session raises ValueError
    - This should result in empty all_frames and target_sessions (since session creation for focus fails)
    """
    session = BrowserSession(browser_profile=BrowserProfile(cross_origin_iframes=False))
    session.agent_focus_target_id = 'focus'

    # _cdp_get_all_pages returns multiple targets; only the focus one should be considered
    targets = [
        {'targetId': 'focus', 'type': 'page'},
        {'targetId': 'other', 'type': 'page'},
        {'targetId': 'iframe1', 'type': 'iframe'},
    ]

    async def fake_cdp_get_all_pages(self, *args, **kwargs):
        return targets

    monkeypatch.setattr(BrowserSession, "_cdp_get_all_pages", fake_cdp_get_all_pages, raising=True)

    async def fake_get_or_create_raise(self, target_id, focus=False):
        # Simulate no session available for focused target
        raise ValueError("no session available")

    monkeypatch.setattr(BrowserSession, "get_or_create_cdp_session", fake_get_or_create_raise, raising=True)

    # Ensure _populate_frame_metadata is present and would raise if called unexpectedly
    async def fake_populate_frame_metadata(self, all_frames, target_sessions):
        raise AssertionError("_populate_frame_metadata should not be called when cross_origin_iframes is False")

    monkeypatch.setattr(BrowserSession, "_populate_frame_metadata", fake_populate_frame_metadata, raising=True)

    all_frames, target_sessions = await session.get_all_frames()

    assert all_frames == {}
    assert target_sessions == {}


@pytest.mark.asyncio
async def test_get_all_frames_without_cross_origin_skips_cross_origin_frames(monkeypatch):
    """
    Test include_cross_origin = False:
    - getFrameTree returns a frame with crossOriginIsolatedContextType set (non-NotIsolated)
    - Frame should be skipped due to cross-origin flag when cross_origin_iframes is False
    """
    session = BrowserSession(browser_profile=BrowserProfile(cross_origin_iframes=False))

    targets = [
        {'targetId': 'p1', 'type': 'page'},
    ]

    async def fake_cdp_get_all_pages(self, *args, **kwargs):
        return targets

    monkeypatch.setattr(BrowserSession, "_cdp_get_all_pages", fake_cdp_get_all_pages, raising=True)

    async def get_frame_tree_with_cross_origin(session_id=None):
        return {
            'frameTree': {
                'frame': {
                    'id': 'fx',
                    'url': 'https://x.example',
                    'crossOriginIsolatedContextType': 'Isolated'
                },
                'childFrames': []
            }
        }

    async def fake_get_or_create_cdp_session(self, target_id, focus=False):
        return FakeCDPSession('s-p1', get_frame_tree_with_cross_origin)

    monkeypatch.setattr(BrowserSession, "get_or_create_cdp_session", fake_get_or_create_cdp_session, raising=True)

    # _populate_frame_metadata should not be called because include_cross_origin False
    async def fake_populate_frame_metadata(self, all_frames, target_sessions):
        raise AssertionError("_populate_frame_metadata should not be called for non-cross-origin run")

    monkeypatch.setattr(BrowserSession, "_populate_frame_metadata", fake_populate_frame_metadata, raising=True)

    all_frames, target_sessions = await session.get_all_frames()

    # Frame was skipped because it was cross-origin and include_cross_origin False
    assert all_frames == {}
    assert target_sessions == {'p1': 's-p1'}
