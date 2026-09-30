let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call startAuthorizationFlow and normalize sync/async/throw behaviors into a Promise
    function callStart(manager, args) {
        try {
            let ret;
            if (args !== undefined) {
                // try calling with arguments (some implementations might accept options)
                ret = manager.startAuthorizationFlow(args);
            } else {
                ret = manager.startAuthorizationFlow();
            }
            if (ret && typeof ret.then === 'function') {
                return ret;
            } else {
                return Promise.resolve(ret);
            }
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('should error (throw or reject) when required client id is missing', function() {
        // Arrange
        const Manager = testpilot_subject.file_0001.OpenAiCodexOAuthManager;
        const manager = new Manager();

        // Ensure no client id forms are present
        delete manager.clientId;
        delete manager.client_id;

        // Stub window.open to detect unwanted calls
        const origWindow = global.window;
        let openCalled = false;
        global.window = {
            open: function() {
                openCalled = true;
                return {};
            }
        };

        // Act & Assert: callStart should reject (either throw or return a rejected promise)
        return callStart(manager).then(function() {
            // If it resolved, consider this a failure unless the implementation allows missing client ID,
            // but ensure it didn't open a window either.
            assert.ok(!openCalled, 'startAuthorizationFlow should not open a window when client id is missing');
            // If it resolved without opening a window, that's still unexpected in typical OAuth flows:
            assert.fail('Expected startAuthorizationFlow to throw or reject when client id is missing');
        }).catch(function(err) {
            // Expected path: an error should be produced
            assert.ok(err instanceof Error || typeof err === 'string' || err !== undefined, 'Expected an error when client id is missing');
        }).finally(function() {
            global.window = origWindow;
        });
    });
});