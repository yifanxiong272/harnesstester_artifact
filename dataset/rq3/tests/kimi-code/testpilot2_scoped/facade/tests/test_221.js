let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // get reference to the function under test (unbound)
    const setPermissionFn = testpilot_subject.file_0002.KimiCore.prototype.setPermission;

    it('forwards sessionId and payload to sessionApi and returns a synchronous result', function() {
        let calledWithSessionId = null;
        const obj = {
            sessionApi(sessionId) {
                calledWithSessionId = sessionId;
                return {
                    setPermission(payload) {
                        // ensure payload has been forwarded (excluding sessionId)
                        assert.deepStrictEqual(payload, { mode: 'yolo' });
                        return 'SYNCHRONOUS_OK';
                    }
                };
            }
        };

        const result = setPermissionFn.call(obj, { sessionId: 'sess-123', mode: 'yolo' });
        assert.strictEqual(calledWithSessionId, 'sess-123', 'sessionApi should be called with the sessionId');
        assert.strictEqual(result, 'SYNCHRONOUS_OK', 'should return the value from inner setPermission');
    });

    })