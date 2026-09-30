let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCoreGetContext = testpilot_subject.file_0002.KimiCore.prototype.getContext;

    it('forwards sessionId to sessionApi and returns getContext result (sync)', function() {
        let seen = {};
        const ctx = {
            sessionApi: function(sessionId) {
                seen.sessionId = sessionId;
                return {
                    getContext: function(payload) {
                        seen.payload = payload;
                        return { ok: true, payloadReceived: payload };
                    }
                };
            }
        };

        const result = KimiCoreGetContext.call(ctx, { sessionId: 'session-123', a: 1, b: 2 });

        assert.strictEqual(seen.sessionId, 'session-123', 'sessionApi should be called with the provided sessionId');
        assert.deepStrictEqual(seen.payload, { a: 1, b: 2 }, 'payload passed to getContext should exclude sessionId and include other properties');
        assert.deepStrictEqual(result, { ok: true, payloadReceived: { a: 1, b: 2 } }, 'return value should be what inner getContext returned');
    });

    })