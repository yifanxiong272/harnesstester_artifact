let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0002.KimiCore.prototype.getGoal;

    it('should call sessionApi with the sessionId and forward the payload, resolving returned plain value', async function() {
        let capturedSessionId = null;
        let capturedPayload = null;

        const ctx = {
            sessionApi: function(sessionId) {
                return {
                    getGoal: function(payload) {
                        capturedSessionId = sessionId;
                        capturedPayload = payload;
                        // return a plain value (not a promise)
                        return { ok: true, from: 'sync' };
                    }
                };
            }
        };

        const result = await fn.call(ctx, { sessionId: 'sess-123', foo: 'bar' });

        assert.deepStrictEqual(result, { ok: true, from: 'sync' }, 'returned value should be forwarded as resolved promise value');
        assert.strictEqual(capturedSessionId, 'sess-123', 'sessionApi should be called with provided sessionId');
        assert.deepStrictEqual(capturedPayload, { foo: 'bar' }, 'payload passed to getGoal should exclude sessionId (rest payload)');
    });

    })