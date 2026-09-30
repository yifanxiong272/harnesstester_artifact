let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep original Array.prototype.push so we can restore it
    let origArrayPush;
    // Record of all push calls during a test
    let pushCalls;

    beforeEach(function() {
        pushCalls = [];
        origArrayPush = Array.prototype.push;
        // Wrap Array.prototype.push to record calls and then forward to original behavior
        Array.prototype.push = function() {
            // record: the array instance (this) and the args passed to push
            // Use the original push implementation to record into pushCalls to avoid
            // infinite recursion (calling pushCalls.push would call this wrapper).
            origArrayPush.call(pushCalls, { targetArray: this, args: Array.prototype.slice.call(arguments) });
            return origArrayPush.apply(this, arguments);
        };
    });

    afterEach(function() {
        // Restore original push implementation even if tests threw
        Array.prototype.push = origArrayPush;
        pushCalls = [];
    });

    it('ToolCallComponent.prototype.appendSubToolCallDelta should exist and be a function', function() {
        let proto = testpilot_subject.file_0003 &&
                    testpilot_subject.file_0003.ToolCallComponent &&
                    testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'ToolCallComponent.prototype is present on module');
        assert.strictEqual(typeof proto.appendSubToolCallDelta, 'function',
            'appendSubToolCallDelta should be a function on the prototype');
    });

});