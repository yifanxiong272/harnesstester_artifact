let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.resumeGoal', function() {
        let KimiCoreProto;
        before(function() {
            // locate the prototype safely
            if (!testpilot_subject
                || !testpilot_subject.file_0002
                || !testpilot_subject.file_0002.KimiCore
                || !testpilot_subject.file_0002.KimiCore.prototype) {
                throw new Error('testpilot_subject.file_0002.KimiCore.prototype not found');
            }
            KimiCoreProto = testpilot_subject.file_0002.KimiCore.prototype;
        });

        // helper to call resumeGoal in a safe way and normalize sync/async behavior
        function callResumeGoalWithThis(thisArg, payload) {
            try {
                const ret = KimiCoreProto.resumeGoal.call(thisArg, payload);
                // if it looks like a Promise, wait for it
                if (ret && typeof ret.then === 'function') {
                    return ret
                        .then(value => ({ outcome: 'resolved', value }))
                        .catch(err => ({ outcome: 'rejected', error: err }));
                } else {
                    // synchronous return
                    return Promise.resolve({ outcome: 'sync', value: ret });
                }
            } catch (err) {
                return Promise.resolve({ outcome: 'threw', error: err });
            }
        }

        it('should export resumeGoal as a function', function() {
            assert.strictEqual(typeof KimiCoreProto.resumeGoal, 'function');
        });

            })
})