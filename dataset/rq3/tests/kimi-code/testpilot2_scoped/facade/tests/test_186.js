let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;

    it('propagates rejected promise from session steer (async)', function() {
        if (!KimiCore) this.skip();

        // Provide a dummy rpcClient function so the constructor doesn't try to call `undefined`
        const instance = new KimiCore(() => {});

        instance.sessionApi = function() {
            return {
                steer() {
                    return Promise.reject(new Error('boom'));
                }
            };
        };

        // assert.rejects returns a promise; return it so mocha waits
        return assert.rejects(
            instance.steer({ sessionId: 's' }),
            /boom/
        );
    });
});