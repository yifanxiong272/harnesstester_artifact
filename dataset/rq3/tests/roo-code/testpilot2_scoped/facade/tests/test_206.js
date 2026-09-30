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
        // Provide a name string to satisfy AsyncResource/constructor options.name requirement
        return new ctor('EventEmitterAsyncResource');
    }

    it('invokes a once listener only one time even if the event is emitted multiple times', function() {
        const emitter = makeEmitter();

        let callCount = 0;
        emitter.once('my-event', function() {
            callCount += 1;
        });

        // Emit multiple times; the listener should only run once
        emitter.em    })
})