let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // reference the actual function under test
    const startBtwFn = testpilot_subject.file_0002.KimiCore.prototype.startBtw;

    it('forwards sessionId to sessionApi and payload (without sessionId) to startBtw and returns its result', function() {
        let seen = {};
        const fakeThis = {
            sessionApi: function(sessionId) {
                seen.sessionId = sessionId;
                return {
                    startBtw: function(payload) {
                        // record what payload was received
                        seen.payload = payload;
                        return 'RESULT_OK';
                    }
                };
            }
        };

        const input = { sessionId: 'SESSION-123', foo: 'bar', count: 5 };
        const result = startBtwFn.call(fakeThis, input);

        // return value should be forwarded
        assert.strictEqual(result, 'RESULT_OK');

        // sessionApi should be called with the sessionId
        assert.strictEqual(seen.sessionId, 'SESSION-123');

        // payload passed to startBtw should NOT contain sessionId (rest operator)
        assert.deepStrictEqual(seen.payload, { foo: 'bar', count: 5 });
    });

    })