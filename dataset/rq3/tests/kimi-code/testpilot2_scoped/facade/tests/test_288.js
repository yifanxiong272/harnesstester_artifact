let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.KimiCore.prototype.getConfig forwards sessionId and payload and returns result', function(done) {
        // create an object that uses the KimiCore prototype without running its constructor
        let inst = Object.create(testpilot_subject.file_0002.KimiCore.prototype);

        const expectedSessionId = 'session-123';
        const expectedPayload = { a: 1, b: 'two' };

        // stub sessionApi to inspect arguments and provide a getConfig implementation
        inst.sessionApi = function(sessionId) {
            // sessionId should be forwarded exactly
            assert.strictEqual(sessionId, expectedSessionId);
            return {
                getConfig: function(payload) {
                    // payload should be the original object minus sessionId
                    assert.deepStrictEqual(payload, expectedPayload);
                    return { ok: true, received: payload };
                }
            };
        };

        const result = inst.getConfig({ sessionId: expectedSessionId, ...expectedPayload });
        assert.deepStrictEqual(result, { ok: true, received: expectedPayload });
        done();
    });

    })