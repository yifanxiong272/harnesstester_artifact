let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.getSessionMetadata', function() {
        it('forwards sessionId to sessionApi and payload (excluding sessionId) to getSessionMetadata and returns the result', function() {
            const KimiCore = testpilot_subject.file_0002.KimiCore;
            // create an instance without running any constructor logic
            const instance = Object.create(KimiCore.prototype);

            let seenSessionId = undefined;
            let seenPayload = undefined;

            instance.sessionApi = function(sessionId) {
                seenSessionId = sessionId;
                return {
                    getSessionMetadata: function(payload) {
                        seenPayload = payload;
                        return { ok: true, received: payload };
                    }
                };
            };

            const input = { sessionId: 'SESSION-123', alpha: 1, beta: 2 };
            const result = instance.getSessionMetadata(input);

            assert.deepStrictEqual(result, { ok: true, received: { alpha: 1, beta: 2 } });
            assert.strictEqual(seenSessionId, 'SESSION-123');
            // payload should exclude sessionId due to destructuring {sessionId, ...payload}
            assert.deepStrictEqual(seenPayload, { alpha: 1, beta: 2 });
        });

            })
})