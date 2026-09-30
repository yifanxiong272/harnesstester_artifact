let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('testpilot_subject.file_0007.MessageProcessor.prototype.handleInvoke', function() {
        it('should exist and be a function on the prototype', function() {
            const proto = testpilot_subject.file_0007 && testpilot_subject.file_0007.MessageProcessor && testpilot_subject.file_0007.MessageProcessor.prototype;
            assert.ok(proto, 'Prototype not found');
            assert.strictEqual(typeof proto.handleInvoke, 'function', 'handleInvoke should be a function');
        });

            })
})