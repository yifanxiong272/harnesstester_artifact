let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create an object that uses KimiCore.prototype without running its constructor
    function makeKimiCoreInstance() {
        return Object.create(testpilot_subject.file_0002.KimiCore.prototype);
    }

    it('should call sessionApi with the provided sessionId and forward the payload (sync return)', function() {
        const instance = makeKimiCoreInstance();

        // Prepare a mock sessionApi that verifies sessionId and payload, and returns a sync value
        instance.sessionApi = function(sessionId) {
            // Verify the sessionId is forwarded correctly
            assert.strictEqual(sessionId, 'session-123');

            return {
                getUsage: function(payload) {
                    // sessionId should have been stripped out; payload should contain only other properties
                    assert.deepStrictEqual(payload, { value: 42, foo: 'bar' });
                    return { ok: true, received: payload };
                }
            };
        };

        const result = instance.getUsage({ sessionId: 'session-123', value: 42, foo: 'bar' });
        assert.deepStrictEqual(result, { ok: true, received: { value: 42, foo: 'bar' } });
    });

    })