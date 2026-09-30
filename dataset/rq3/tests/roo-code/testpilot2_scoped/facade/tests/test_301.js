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

        it('propagates errors thrown by underlying AsyncResource.emitDestroy', function(done) {
            if (!AsyncResource) return done();

            const original = AsyncResource.prototype.emitDestroy;
            const testError = new Error('underlying error');
            AsyncResource.prototype.emitDestroy = function() {
                throw testError;
            };

            try {
                const Cls = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

                // Some AsyncResource-based subclasses require a "name" argument.
                // Try to construct with no args first, and if that fails with the
                // options.name error, retry providing a name.
                let inst;
                try {
                    inst = new Cls();
                } catch (err) {
                    // If the error mentions options.name, retry with a name string.
                    if (err && typeof err.message === 'string' && /options\.name/.test(err.message)) {
                        try {
                            inst = new Cls('EventEmitterAsyncResource');
                        } catch (err2) {
                            // As a last resort, try passing an options object with name.
                            inst = new Cls({ name: 'EventEmitterAsyncResource' });
                        }
                    } else {
                        throw err;
                    }
                }

                let threw = false;
                try {
                    inst.emitDestroy();
                } catch (err) {
                    threw = true;
                    assert.strictEqual(err, testError, 'Error should be exactly the one thrown by underlying emitDestroy');
                }

                assert.ok(threw, 'emitDestroy should throw when underlying emitDestroy throws');
                done();
            } catch (err) {
                done(err);
            } finally {
                AsyncResource.prototype.emitDestroy = original;
            }
        });
    });
});