let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('forwards sessionId to sessionApi and payload (sync return)', function() {
        const KimiCoreProto = testpilot_subject.file_0002.KimiCore.prototype;

        let seenSessionId = null;
        let seenPayload = null;

        const fakeThis = {
            sessionApi(sessionId) {
                seenSessionId = sessionId;
                return {
                    beginCompaction(payload) {
                        seenPayload = payload;
                        return 'SYNC_OK';
                    }
                };
            }
        };

        const result = KimiCoreProto.beginCompaction.call(fakeThis, { sessionId: 'S1', alpha: 1, beta: 2 });

        // verify return value is forwarded
        assert.strictEqual(result, 'SYNC_OK');

        // verify sessionApi called with correct sessionId
        assert.strictEqual(seenSessionId, 'S1');

        // verify the payload passed to beginCompaction does not contain sessionId (destructuring removed it)
        assert.deepStrictEqual(seenPayload, { alpha: 1, beta: 2 });
    });

    })