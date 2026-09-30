let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('calls sessionApi with sessionId and passes payload without sessionId', function() {
        const KimiCoreProto = testpilot_subject.file_0002.KimiCore.prototype;
        // create a plain instance that uses the prototype method but does not run any constructor
        const instance = Object.create(KimiCoreProto);

        let capturedSessionId = Symbol('none');
        let capturedPayload = Symbol('none');

        // stub sessionApi to capture the sessionId and return an object with activateSkill
        instance.sessionApi = function(sessionId) {
            capturedSessionId = sessionId;
            return {
                activateSkill: function(payload) {
                    capturedPayload = payload;
                    return 'ok-sync';
                }
            };
        };

        const result = instance.activateSkill({sessionId: 'ABC', foo: 42, extra: 'x'});

        // sessionId should be forwarded
        assert.strictEqual(capturedSessionId, 'ABC');
        // payload passed to activateSkill should NOT include sessionId (it was destructured away)
        assert.deepStrictEqual(capturedPayload, { foo: 42, extra: 'x' });
        // return value should be forwarded
        assert.strictEqual(result, 'ok-sync');
    });

    })