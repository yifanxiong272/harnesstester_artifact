let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should have notifyTaskCleared on MessageProcessor prototype', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0007, 'file_0007 namespace should exist');
        let mpProto = testpilot_subject.file_0007.MessageProcessor && testpilot_subject.file_0007.MessageProcessor.prototype;
        assert.ok(mpProto, 'MessageProcessor.prototype should exist');
        assert.strictEqual(typeof mpProto.notifyTaskCleared, 'function', 'notifyTaskCleared should be a function');
        // basic arity check (defensive, not required to pass)
        assert.ok(mpProto.notifyTaskCleared.length >= 0);
    });

    })