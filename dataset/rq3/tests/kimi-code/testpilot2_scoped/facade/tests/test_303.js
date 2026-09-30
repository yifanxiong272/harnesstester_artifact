let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject.file_0002.KimiCore;
    const proto = KimiCore.prototype;
    const originalSessionApi = proto.sessionApi;

    after(function() {
        // restore original to avoid side effects on other tests
        proto.sessionApi = originalSessionApi;
    });

    it('forwards sessionId and payload correctly and returns the inner result', function() {
        // Arrange
        let observedSessionId = undefined;
        let observedPayload = undefined;

        proto.sessionApi = function(sessionId) {
            observedSessionId = sessionId;
            return {
                getTools: function(payload) {
                    observedPayload = payload;
                    return { ok: true, returnedSessionId: sessionId, returnedPayload: payload };
                }
            };
        };

        // Create an instance without running constructor (keeps test self-contained)
        const instance = Object.create(proto);

        // Act
        const result = instance.getTools({ sessionId: 'SID-123', a: 1, b: 2 });

        // Assert
        assert.strictEqual(observedSessionId, 'SID-123', 'sessionApi should be called with the sessionId');
        assert.deepStrictEqual(observedPayload, { a: 1, b: 2 }, 'payload passed to getTools should exclude sessionId and include rest');
        assert.deepStrictEqual(result, { ok: true, returnedSessionId: 'SID-123', returnedPayload: { a: 1, b: 2 } }, 'result should be whatever inner getTools returns');
    });

    })