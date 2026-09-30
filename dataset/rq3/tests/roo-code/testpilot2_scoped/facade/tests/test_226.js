let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EmitterClass = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('does not throw when removing listeners and none are registered', function(done) {
        // Avoid calling the constructor (which internally tries to create an AsyncResource
        // and fails when options.name is undefined). Create an object with the same prototype
        // so prototype methods (listeners/removeAllListeners) can be used without running the ctor.
        const emitter = Object.create(EmitterClass.prototype);

        // No listeners registered at all
        assert.strictEqual((emitter.listeners('nothing') || []).length, 0);

        // Should not throw
        emitter.removeAllListeners('nothing');
        emitter.removeAllListeners();

        // Still no listeners
        assert.strictEqual((emitter.listeners('nothing') || []).length, 0);

        done();
    });
});