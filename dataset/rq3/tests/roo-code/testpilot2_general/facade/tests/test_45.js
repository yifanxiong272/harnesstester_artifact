let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const ManagerClass = testpilot_subject.file_0001.OpenAiCodexOAuthManager;

    it('startAuthorizationFlow should call cancelAuthorizationFlow and set pendingAuth with codeVerifier and state', function() {
        const mgr = new ManagerClass();

        // Replace instance cancelAuthorizationFlow with a spy so we can see it was called.
        let cancelCalled = 0;
        mgr.cancelAuthorizationFlow = function() { cancelCalled += 1; };

        const ret = mgr.startAuthorizationFlow();

        // cancelAuthorizationFlow should have been called once
        assert.strictEqual(cancelCalled, 1, 'cancelAuthorizationFlow should be called once');

        // pendingAuth should be set and contain codeVerifier and state
        assert.ok(mgr.pendingAuth, 'pendingAuth should be set');
        assert.strictEqual(typeof mgr.pendingAuth.codeVerifier, 'string', 'codeVerifier should be a string');
        assert.ok(mgr.pendingAuth.codeVerifier.length > 0, 'codeVerifier should be non-empty');
        assert.strictEqual(typeof mgr.pendingAuth.state, 'string', 'state should be a string');
        assert.ok(mgr.pendingAuth.state.length > 0, 'state should be non-empty');

        // The method should return something (presumably an authorization URL string)
        assert.strictEqual(typeof ret, 'string', 'startAuthorizationFlow should return a string');
        assert.ok(ret.length > 0, 'returned string should be non-empty');
    });

    })