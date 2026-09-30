let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EmitterClass = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('emits event to listeners with correct arguments and `this` context', function() {
        // Provide a name so any underlying AsyncResource/options validation succeeds
        const emitter = new EmitterClass('EventEmitter');

        let called = 0;
        let receivedArgs = null;
        let receivedThis = null;

        emitter.on('ping', function(a, b, c) {
            called++;
            receivedArgs = [a, b, c];
            receivedThis = this;
        });

        const returnVal = emitter.em    })
})