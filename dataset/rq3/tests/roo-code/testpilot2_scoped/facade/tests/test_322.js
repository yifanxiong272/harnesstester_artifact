let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0012.MessageQueueService.prototype.addMessage', function() {
    const MessageQueueService = testpilot_subject.file_0012.MessageQueueService;

    it('returns undefined and does not emit when neither text nor images are provided', function() {
        const svc = new MessageQueueService();
        const emitted = [];
        svc.emit = function() { emitted.push(Array.from(arguments)); };

        const result = svc.addMessage();
        assert.strictEqual(result, undefined, 'Expected undefined when no args provided');
        assert.ok(Array.isArray(svc._messages), '_messages should exist and be an array');
        assert.strictEqual(svc._messages.length, 0, 'No message should be added');
        assert.strictEqual(emitted.length, 0, 'No events should be emitted');
    });

    })