let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const createGoal = testpilot_subject.file_0002.KimiCore.prototype.createGoal;

    it('resolves with the value returned by the underlying createGoal', function() {
        // fake "this" with sessionApi returning an object with createGoal
        const fakeThis = {
            sessionApi: function(sessionId) {
                // ensure sessionId was passed correctly (sanity)
                assert.strictEqual(sessionId, 'session-1');
                return {
                    createGoal: function(payload) {
                        // payload should be the rest of the properties (destructured)
                        assert.deepStrictEqual(payload, { a: 1, b: 2 });
                        return { ok: true, payload };
                    }
                };
            }
        };

        // call the prototype method with a parameter object
        return createGoal.call(fakeThis, { sessionId: 'session-1', a: 1, b: 2 })
            .then(result => {
                assert.deepStrictEqual(result, { ok: true, payload: { a: 1, b: 2 } });
            });
    });

    })