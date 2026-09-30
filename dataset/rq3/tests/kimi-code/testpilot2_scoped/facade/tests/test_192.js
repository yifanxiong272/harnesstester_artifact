let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject.file_0002.KimiCore;

    it('calls sessionApi with provided sessionId and forwards payload without sessionId', function() {
        // Avoid invoking the real constructor (which expects rpcClient to be a function)
        // by creating an object with the correct prototype so we can override sessionApi.
        const instance = Object.create(KimiCore.prototype);

        let captured = { sid: undefined, payload: undefined };
        instance.sessionApi = function(sessionId) {
            captured.sid = sessionId;
            return {
                steer: function(payload) {
                    captured.payload = payload;
                    return 'ok-result';
                }
            };
        };

        const result = instance.steer({ sessionId: 'sess-123', a: 1, b: 2 });

        assert.strictEqual(captured.sid, 'sess-123', 'sessionId should be forwarded to sessionApi');
        assert.deepStrictEqual(captured.payload, { a: 1, b: 2 }, 'payload passed to sessionApi.steer should exclude sessionId');
        assert.strictEqual(result, 'ok-result', 'return value from sessionApi.steer should be returned');
    });

    })