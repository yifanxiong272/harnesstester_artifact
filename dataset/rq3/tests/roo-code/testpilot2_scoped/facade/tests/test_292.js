let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.prototype.emit', function() {
    const Emitter = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('emit should return false when there are no listeners for the event', function() {
        // Provide a name to the constructor (AsyncResource-derived classes expect a string name)
        const emitter = new Emitter('test-emitter');
        const ret = emitter.em    })
})