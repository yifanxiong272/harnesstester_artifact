let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject.file_0002.KimiCore;
    const registerTool = KimiCore.prototype.registerTool;

    it('calls sessionApi with sessionId and forwards payload to registerTool (sync return)', function() {
        const expectedSessionId = 'session-123';
        const expectedPayload = { tool: 'hammer', version: 2 };

        let seenSessionId = null;
        let seenPayload = null;

        const fakeThis = {
            sessionApi: function(sessionId) {
                seenSessionId = sessionId;
                return {
                    registerTool: function(payload) {
                        seenPayload = payload;
                        return 'sync-result';
                    }
                };
            }
        };

        const result = registerTool.call(fakeThis, { sessionId: expectedSessionId, ...expectedPayload });

        assert.strictEqual(result, 'sync-result', 'should return value from registerTool');
        assert.strictEqual(seenSessionId, expectedSessionId, 'sessionApi should be called with the sessionId');
        assert.deepStrictEqual(seenPayload, expectedPayload, 'registerTool should be called with the payload excluding sessionId');
    });

    })