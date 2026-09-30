let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
    if (!KimiCore) {
        // If the class is not present, make tests fail early with a clear message.
        throw new Error('testpilot_subject.file_0002.KimiCore is not available');
    }

    // keep original to restore after tests
    const originalResumeWithOverrides = KimiCore.prototype.resumeSessionWithOverrides;

    afterEach(function() {
        // restore original to avoid side effects across tests
        KimiCore.prototype.resumeSessionWithOverrides = originalResumeWithOverrides;
    });

    it('forwards input and an empty overrides object to resumeSessionWithOverrides and returns its resolved value', async function() {
        let captured = {};
        // stub the underlying method
        KimiCore.prototype.resumeSessionWithOverrides = function(input, overrides) {
            captured.input = input;
            captured.overrides = overrides;
            // ensure the stub returns a promise (async behavior)
            return Promise.resolve({ ok: true, echoed: input });
        };

        // create a plain instance that uses the prototype (avoids constructor requirements)
        const instance = Object.create(KimiCore.prototype);
        const inputObj = { sessionId: 'abc', value: 123 };
        const result = await instance.resumeSession(inputObj);

        // check that the input was forwarded by reference
        assert.strictEqual(captured.input, inputObj, 'input argument was not forwarded correctly');

        // check that overrides is an object and is empty
        assert.strictEqual(typeof captured.overrides, 'object');
        assert.deepStrictEqual(captured.overrides, {}, 'overrides should be an empty object');

        // check return value passed through
        assert.deepStrictEqual(result, { ok: true, echoed: inputObj });
    });

    })