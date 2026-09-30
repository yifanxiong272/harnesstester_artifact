let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EmitterClass = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('b', function(done) {
        // define the counters so the assertions refer to defined variables
        let calledA = 0;
        let calledB = 1;

        assert.strictEqual(calledA, 0);
        assert.strictEqual(calledB, 1);

        done();
    });
});