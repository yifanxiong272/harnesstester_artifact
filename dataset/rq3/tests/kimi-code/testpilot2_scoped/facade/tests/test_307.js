let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const update = testpilot_subject.file_0002.KimiCore.prototype.updateSessionMetadata;

    it('calls sessionApi with the sessionId and forwards payload without sessionId (sync return)', function() {
        let capturedSessionId = undefined;
        let capturedPayload = undefined;

        const fakeThis = {
            sessionApi: function(sid) {
                capturedSessionId = sid;
                return {
                    updateSessionMetadata: function(payload) {
                        capturedPayload = payload;
                        return 'sync-ok';
                    }
                };
            }
        };

        const input = { sessionId: 'session-123', foo: 'bar', count: 7 };
        const result = update.call(fakeThis, input);

        // return value should be whatever the inner update returned
        assert.strictEqual(result, 'sync-ok');

        // sessionApi should have been called with the sessionId only
        assert.strictEqual(capturedSessionId, 'session-123');

        // payload passed to updateSessionMetadata should NOT contain sessionId
        assert.deepStrictEqual(capturedPayload, { foo: 'bar', count: 7 });
    });

    })