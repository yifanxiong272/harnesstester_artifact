let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.startBtw', function() {
        let KimiCore;
        before(function() {
            // Basic existence checks for module shape
            assert.ok(testpilot_subject, 'testpilot_subject must be present');
            assert.ok(testpilot_subject.file_0002, 'testpilot_subject.file_0002 must be present');
            KimiCore = testpilot_subject.file_0002.KimiCore;
            assert.ok(KimiCore, 'KimiCore must be exported');
            assert.strictEqual(typeof KimiCore.prototype.startBtw, 'function', 'startBtw must be a function on the prototype');
        });

        it('should throw or reject when called with no argument or a non-object in a predictable way', async function() {
            // Many implementations that destructure the single argument will throw when undefined.
            // We accept either a synchronous throw or a rejected promise.
            let instance;
            try {
                instance = new KimiCore();
            } catch (e) {
                instance = Object.create(KimiCore.prototype);
            }

            let threwSync = false;
            let rejected = false;
            try {
                const r = instance.startBtw(); // call with undefined
                if (r && typeof r.then === 'function') {
                    // If promise-like, await and catch rejection
                    await r.then(
                        () => {},
                        () => { rejected = true; }
                    );
                }
            } catch (e) {
                threwSync = true;
            }

            // At least one of the behaviors should happen: a sync throw or a rejection.
            assert.ok(threwSync || rejected, 'Calling startBtw() without an argument should either throw synchronously or return a rejected promise');
        });
    });
});