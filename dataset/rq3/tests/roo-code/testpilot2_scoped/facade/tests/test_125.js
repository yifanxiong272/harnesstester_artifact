let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('initial state is empty and messages getter works', function() {
        const svc = new testpilot_subject.file_0012.MessageQueueService();
        assert.strictEqual(svc.isEmpty(), true);
        assert.ok(Array.isArray(svc.messages));
        assert.strictEqual(svc.messages.length, 0);
    });

    })