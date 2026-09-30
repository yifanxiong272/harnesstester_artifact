let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0012.MessageQueueService.prototype.isEmpty', function() {
    // Get the prototype under test
    const proto = testpilot_subject &&
                  testpilot_subject.file_0012 &&
                  testpilot_subject.file_0012.MessageQueueService &&
                  testpilot_subject.file_0012.MessageQueueService.prototype;

    it('should have the MessageQueueService.prototype available', function() {
        assert.ok(proto, 'MessageQueueService.prototype is not available on testpilot_subject.file_0012');
        assert.strictEqual(typeof proto.isEmpty, 'function', 'isEmpty is not a function on the prototype');
    });

    })