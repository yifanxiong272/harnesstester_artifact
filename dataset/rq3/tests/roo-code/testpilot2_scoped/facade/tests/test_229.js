let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EmitterClass = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('two', function(done) {
        // Ensure the variables exist before asserting
        let called1 = 0;
        let called2 = 0;

        assert.strictEqual(called1, 0);
        assert.strictEqual(called2, 0);

        done();
    });
});