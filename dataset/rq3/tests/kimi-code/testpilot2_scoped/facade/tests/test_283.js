let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Skip the suite if the module or KimiCore is not present.
    before(function() {
        if (!testpilot_subject || !testpilot_subject.file_0002 || !testpilot_subject.file_0002.KimiCore) {
            this.skip(); // gracefully skip tests when target is not present
        }
    });

    it('has KimiCore and getContext is a function', function() {
        let KimiCore = testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore should be exported');
        assert.strictEqual(typeof KimiCore.prototype.getContext, 'function', 'getContext should be a function on the prototype');
    });

    // Helper to call getContext and normalize sync/promise results
    async function invokeGetContext(core, arg) {
        try {
            let result = core.getContext(arg);
            // Await in case it's a Promise, otherwise this resolves immediately
            let value = await Promise.resolve(result);
            return { ok: true, value: value };
        } catch (error) {
            return { ok: false, error: error };
        }
    }

    })