let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0002.KimiCore.prototype.detachBackground;

    it('should forward payload and return value when detachBackground returns synchronously', function() {
        // Arrange: create a fake `this` with sessionApi that returns an object
        // whose detachBackground captures the payload and returns a value.
        let captured = null;
        const fakeThis = {
            sessionApi: function(sessionId) {
                // verify that correct sessionId is passed through
                assert.strictEqual(sessionId, 'session-123');
                return {
                    detachBackground: function(payload) {
                        captured = payload;
                        return {result: 'ok'};
                    }
                };
            }
        };

        // Act
        const payload = {a: 1, b: 2};
        const result = fn.call(fakeThis, {sessionId: 'session-123', ...payload});

        // Assert
        assert.deepStrictEqual(captured, payload);
        assert.deepStrictEqual(result, {result: 'ok'});
    });

    })