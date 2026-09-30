let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
    if (!KimiCore) {
        throw new Error('testpilot_subject.file_0002.KimiCore is not available');
    }

    it('forwards sessionId to sessionApi and payload (without sessionId) to listMcpServers and returns a sync result', function() {
        // create an instance without running the original constructor to avoid side effects
        const inst = Object.create(KimiCore.prototype);

        let capturedSessionId = null;
        let capturedPayload = null;

        inst.sessionApi = function(sessionId) {
            capturedSessionId = sessionId;
            return {
                listMcpServers: function(payload) {
                    capturedPayload = payload;
                    return 'SYNC_OK';
                }
            };
        };

        const result = inst.listMcpServers({ sessionId: 'SESSION-1', alpha: 42 });

        assert.strictEqual(capturedSessionId, 'SESSION-1', 'sessionId should be forwarded to sessionApi');
        assert.deepStrictEqual(capturedPayload, { alpha: 42 }, 'payload passed to listMcpServers should exclude sessionId');
        assert.strictEqual(result, 'SYNC_OK', 'return value should be the value returned by inner listMcpServers');
    });

    })