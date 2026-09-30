let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const MessageQueueService = testpilot_subject.file_0012.MessageQueueService;

    it('MessageQueueService.dispose exists and is callable', function() {
        let svc = new MessageQueueService();
        assert.strictEqual(typeof svc.dispose, 'function', 'dispose should be a function');
        // calling dispose should not throw
        assert.doesNotThrow(() => svc.dispose());
    });

    })