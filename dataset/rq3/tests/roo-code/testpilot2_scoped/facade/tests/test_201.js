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
        // Provide a name so AsyncResource/constructor doesn't receive an undefined name
        // (some implementations require a string name or options.name)
        return new ctor('test-emitter');
    }

    it('throws a TypeError when listener is not a function', function() {
        const emitter = makeEmitter();

        // Passing non-function should throw (behavior consistent with Node EventEmitter)
        assert.throws(
            () => emitter.once('bad', null),
            {
                name: 'TypeError'
            },
            'once should throw a TypeError when listener is not a function'
        );
    });
});