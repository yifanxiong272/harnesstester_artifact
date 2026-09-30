let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0002.KimiCore.prototype.setThinking;

    it('forwards sessionId to sessionApi and forwards payload (without sessionId) to setThinking, returns sync result', function() {
        let observed = null;
        const fakeThis = {
            sessionApi(sessionId) {
                return {
                    setThinking(payload) {
                        observed = { sessionId, payload };
                        return 'SYNCHRONOUS_RESULT';
                    }
                };
            }
        };

        const result = fn.call(fakeThis, { sessionId: 'session-123', level: 'high', flag: true });

        // returned value
        assert.strictEqual(result, 'SYNCHRONOUS_RESULT');

        // sessionId forwarded to sessionApi
        assert.strictEqual(observed.sessionId, 'session-123');

        // payload passed to setThinking should NOT include sessionId
        assert.deepStrictEqual(observed.payload, { level: 'high', flag: true });
        assert.strictEqual(Object.prototype.hasOwnProperty.call(observed.payload, 'sessionId'), false);
    });

    })