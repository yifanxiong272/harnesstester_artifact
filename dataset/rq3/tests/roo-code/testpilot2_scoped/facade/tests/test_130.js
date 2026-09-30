let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0012.MessageQueueService.on', function() {
        it('should exist and be a function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0012, 'file_0012 namespace is present');
            const svc = testpilot_subject.file_0012.MessageQueueService;
            assert.ok(svc, 'MessageQueueService is present');
            assert.strictEqual(typeof svc.on, 'function', 'on should be a function');
        });

            })
})