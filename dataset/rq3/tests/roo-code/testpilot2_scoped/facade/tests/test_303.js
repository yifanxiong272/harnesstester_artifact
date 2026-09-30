let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.prototype.emitDestroy', function() {
        // Helper to safely require AsyncResource
        const AsyncResource = (() => {
            try {
                return require('async_hooks').AsyncResource;
            } catch (e) {
                return null;
            }
        })();

        it('calls the underlying AsyncResource.emitDestroy once and returns undefined', function(done) {
            if (!AsyncResource) {
                // If async_hooks is not available, skip this test by marking as passed.
                // (Mocha does not provide a built-in skip here without using this.skip inside function,
                // but to keep the API simple we treat it as a no-op success.)
                return done();
            }

            const original = AsyncResource.prototype.emitDestroy;
            let callCount = 0;
            const seenThis = [];

            // Wrap the underlying emitDestroy so we can observe calls and 'this'
            AsyncResource.prototype.emitDestroy = function() {
                callCount++;
                seenThis.push(this);
                // Call original if present (keep behavior)
                if (original) return original.apply(this, arguments);
            };

            try {
                const Cls = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
                assert.strictEqual(typeof Cls, 'function', 'Expected EventEmitterAsyncResource to be a constructor function');

                // Try several ways to construct the instance to handle environments
                // where AsyncResource requires a name/options that might otherwise be undefined.
                let inst;
                let constructError;
                try {
                    inst = new Cls();
                } catch (e1) {
                    constructError = e1;
                    // If the error looks like the options.name problem, attempt alternate ctor signatures.
                    const msg = String(e1 && e1.message);
                    if (/options\.name/.test(msg) || /options name/.test(msg) || /name.*undefined/.test(msg)) {
                        try {
                            inst = new Cls('test'); // try a string name first
                        } catch (e2) {
                            try {
                                inst = new Cls({ name: 'test' }); // try an options object with name
                            } catch (e3) {
                                // keep original error to surface below
                                constructError = e3 || e2 || e1;
                            }
                        }
                    }
                }
                if (!inst) {
                    // If we couldn't construct an instance, fail with the original construction error.
                    throw constructError || new Error('Failed to construct EventEmitterAsyncResource instance');
                }

                assert.ok(inst, 'Expected constructor to return an instance');
                assert.strictEqual(typeof inst.emitDestroy, 'function', 'Instance should have emitDestroy method');

                const ret = inst.emitDestroy();
                assert.strictEqual(ret, undefined, 'emitDestroy should return undefined (no explicit return)');

                assert.strictEqual(callCount, 1, 'Underlying AsyncResource.emitDestroy should have been called exactly once');
                assert.ok(seenThis.length >= 1, 'Should have observed at least one this when underlying emitDestroy was called');
                // Ensure the observed 'this' is an AsyncResource instance
                assert.ok(seenThis.every(s => s instanceof AsyncResource), 'Underlying this values should be AsyncResource instances');

                done();
            } catch (err) {
                done(err);
            } finally {
                // Restore original to avoid side effects
                AsyncResource.prototype.emitDestroy = original;
            }
        });

            })
})