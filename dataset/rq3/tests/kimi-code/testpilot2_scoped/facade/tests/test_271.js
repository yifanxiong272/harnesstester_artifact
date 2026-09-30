let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0002.KimiCore.prototype.setActiveTools', function() {
    // Create an "instance" without running any real constructor code to avoid external side effects
    const KimiCoreProto = testpilot_subject.file_0002.KimiCore.prototype;

    it('forwards sessionId and payload to sessionApi.setActiveTools and returns the result (sync)', function() {
        const instance = Object.create(KimiCoreProto);

        let seenSessionIds = [];
        let seenPayloads = [];

        // stub sessionApi to capture sessionId and payload, and return a synchronous result
        instance.sessionApi = function(sessionId) {
            seenSessionIds.push(sessionId);
            return {
                setActiveTools: function(payload) {
                    seenPayloads.push(payload);
                    return 'SYNCHRONOUS_RESULT';
                }
            };
        };

        const input = { sessionId: 'session-123', toolA: true, value: 42 };
        const result = KimiCoreProto.setActiveTools.call(instance, input);

        assert.strictEqual(result, 'SYNCHRONOUS_RESULT');
        assert.strictEqual(seenSessionIds.length, 1);
        assert.strictEqual(seenSessionIds[0], 'session-123');
        assert.deepStrictEqual(seenPayloads[0], { toolA: true, value: 42 });
    });

    })