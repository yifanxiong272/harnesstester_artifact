let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EmitterClass = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('x', function(done) {
        // define the variable used by the assertion
        let calledX = 1;

        // (optional) use EmitterClass here to change calledX as needed

        assert.strictEqual(calledX, 1);
        done();
    });
});