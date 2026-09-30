let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const cancelCompaction = testpilot_subject.file_0002.KimiCore.prototype.cancelCompaction;

    it('calls sessionApi with the provided sessionId and passes empty payload when no extra fields', function() {
        let calledSessionId = null;
        let receivedPayload = null;

        // fake `this` with sessionApi that returns an object with cancelCompaction
        const fakeThis = {
            sessionApi: function(sessionId) {
                calledSessionId = sessionId;
                return {
                    cancelCompaction: function(payload) {
                        receivedPayload = payload;
                        return 'SYNC_OK';
                    }
                };
            }
        };

        const result = cancelCompaction.call(fakeThis, { sessionId: 'sess-123' });

        // verify sessionApi called with correct id
        assert.strictEqual(calledSessionId, 'sess-123');
        // payload should be an empty object (rest collects nothing)
        assert.deepStrictEqual(receivedPayload, {});
        // return value should be proxied through
        assert.strictEqual(result, 'SYNC_OK');
    });

    })