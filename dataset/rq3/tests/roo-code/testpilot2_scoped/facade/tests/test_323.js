let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0012.MessageQueueService.prototype.removeMessage', function() {

        it('should exist and be a function', function() {
            assert.ok(testpilot_subject, 'testpilot_subject module should be present');
            assert.ok(testpilot_subject.file_0012, 'file_0012 should be present on testpilot_subject');
            let Service = testpilot_subject.file_0012.MessageQueueService;
            assert.ok(Service, 'MessageQueueService should be present');
            assert.strictEqual(typeof Service.prototype.removeMessage, 'function',
                'removeMessage should be a function on the prototype');
        });

            })
})