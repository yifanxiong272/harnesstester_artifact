let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.prototype.once', function() {
    // Helper to construct an emitter instance
    function makeEmitter() {
        // Navigate to the constructor exposed by the package
        const ctor = testpilot_subject
            && testpilot_subject.file_0012
            && testpilot_subject.file_0012.MessageQueueService
            && testpilot_subject.file_0012.MessageQueueService.EventEmitter
            && testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
        if (typeof ctor !== 'function') {
            throw new Error('EventEmitterAsyncResource constructor not found on testpilot_subject');
        }

        // Some implementations of AsyncResource-derived constructors expect a name/type string
        // or an options object with a name property. Try a sensible string first and fall back
        // to an options object if needed.
        try {
            return new ctor('test-emitter');
        } catch (err) {
            // If the constructor expects an options object instead, try that.
            try {
                return new ctor({ name: 'test-emitter' });
            } catch (err2) {
                // Re-throw the original error if both attempts fail
                throw err;
            }
        }
    }

    it('returns the emitter instance from once (allows chaining)', function() {
        const emitter = makeEmitter();

        function listener() {}
        const ret = emitter.once('chain-event', listener);

        // Expect that once returns the emitter itself (common EventEmitter behavior)
        assert.strictEqual(ret, emitter, 'once should return the emitter instance for chaining');
    });

})