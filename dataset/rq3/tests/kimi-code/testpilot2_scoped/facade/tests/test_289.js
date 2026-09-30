let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // get reference to the function under test
    const getConfig = testpilot_subject.file_0002.KimiCore.prototype.getConfig;

    it('calls sessionApi with provided sessionId and forwards payload without sessionId (sync)', function() {
        let seenSessionId = Symbol('none');
        let seenPayload = null;

        // fake context with sessionApi
        const ctx = {
            sessionApi(sessionId) {
                seenSessionId = sessionId;
                return {
                    getConfig(payload) {
                        seenPayload = payload;
                        return { ok: true, forwarded: payload };
                    }
                };
            }
        };

        const input = { sessionId: 'session-123', a: 1, b: 'two' };
        const result = getConfig.call(ctx, input);

        // verify sessionApi got called with sessionId
        assert.strictEqual(seenSessionId, 'session-123');

        // verify the payload forwarded to inner getConfig does NOT include sessionId
        assert.deepStrictEqual(seenPayload, { a: 1, b: 'two' });

        // verify return value is the getConfig result
        assert.deepStrictEqual(result, { ok: true, forwarded: { a: 1, b: 'two' } });
    });

    })