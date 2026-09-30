let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.resumeGoal', function() {
        const KimiCore = testpilot_subject &&
                        testpilot_subject.file_0002 &&
                        testpilot_subject.file_0002.KimiCore;

        it('calls sessionApi with sessionId and calls resumeGoal with the payload (sync return)', function() {
            if (!KimiCore) this.skip();

            // create a bare instance without running any constructor
            const instance = Object.create(KimiCore.prototype);

            let seenSessionId = null;
            let seenPayload = null;
            const returnValue = 12345;

            instance.sessionApi = function(sessionId) {
                seenSessionId = sessionId;
                return {
                    resumeGoal: function(payload) {
                        seenPayload = payload;
                        return returnValue; // synchronous return
                    }
                };
            };

            return instance.resumeGoal({ sessionId: 'my-session', alpha: 'beta' })
                .then(result => {
                    assert.strictEqual(result, returnValue, 'should resolve to the value returned by resumeGoal');
                    assert.strictEqual(seenSessionId, 'my-session', 'sessionApi should be called with the provided sessionId');
                    assert.deepStrictEqual(seenPayload, { alpha: 'beta' }, 'resumeGoal should be called with the payload (without sessionId)');
                });
        });

            })
})