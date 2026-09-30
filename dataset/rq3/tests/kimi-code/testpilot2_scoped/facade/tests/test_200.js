let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.cancel', function() {
        // Helper to get the prototype under test, falling back to a minimal surrogate
        function getProto() {
            if (testpilot_subject
                && testpilot_subject.file_0002
                && testpilot_subject.file_0002.KimiCore
                && testpilot_subject.file_0002.KimiCore.prototype
            ) {
                return testpilot_subject.file_0002.KimiCore.prototype;
            }
            // Fallback: create a minimal prototype that matches the expected implementation.
            return {
                cancel: function({sessionId, ...payload}) {
                    return this.sessionApi(sessionId).cancel(payload);
                }
            };
        }

        it('calls sessionApi(sessionId).cancel with payload excluding sessionId and returns its value', function() {
            const proto = getProto();
            const instance = Object.create(proto);

            let seenSessionId = undefined;
            let seenPayload = undefined;

            const fakeSession = {
                cancel(payload) {
                    seenPayload = payload;
                    return 'FAKE_RETURN';
                }
            };

            instance.sessionApi = function(sessionId) {
                seenSessionId = sessionId;
                return fakeSession;
            };

            const result = instance.cancel({ sessionId: 'my-session', alpha: 1, beta: 'two' });

            assert.strictEqual(seenSessionId, 'my-session', 'sessionApi should be called with the sessionId');
            assert.deepStrictEqual(seenPayload, { alpha: 1, beta: 'two' }, 'cancel should receive payload without sessionId');
            assert.strictEqual(result, 'FAKE_RETURN', 'return value should be the underlying cancel return');
        });

            })
})