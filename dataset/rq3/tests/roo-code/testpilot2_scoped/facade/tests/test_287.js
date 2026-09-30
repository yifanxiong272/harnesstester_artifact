let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EmitterClass = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('returns false when emitting an event with no listeners', function() {
        // AsyncResource (or similar) implementations often require a name string.
        const emitter = new EmitterClass('test-emitter');
        const returnVal = emitter.em    })
})