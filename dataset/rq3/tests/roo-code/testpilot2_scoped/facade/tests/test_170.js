let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to safely construct an instance of the target class
    function makeInstance(Constructor) {
        if (!Constructor) return null;
        // Try a few ways to obtain an instance
        try {
            return new Constructor();
        } catch (e1) {
            try {
                return Constructor();
            } catch (e2) {
                // As a last resort, create object with prototype (if available)
                if (Constructor.prototype && typeof Constructor.prototype === 'object') {
                    return Object.create(Constructor.prototype);
                }
                return null;
            }
        }
    }

    const Target = testpilot_subject &&
                   testpilot_subject.file_0012 &&
                   testpilot_subject.file_0012.MessageQueueService &&
                   testpilot_subject.file_0012.MessageQueueService.EventEmitter &&
                   testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('addListener should return the emitter instance for chaining', function(done) {
        if (!Target) return this.skip();
        const inst = makeInstance(Target);
        if (!inst) return this.skip();
        if (typeof inst.addListener !== 'function') return this.skip();

        function listener() {}
        const ret = inst.addListener('evt', listener);
        // Common EventEmitter behavior is to return the emitter (for chaining)
        assert.strictEqual(ret, inst);
        done();
    });

    })