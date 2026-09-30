let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.stopStreamingProgressTimer', function() {
        it('is a function on the prototype', function() {
            let proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
            assert.strictEqual(typeof proto.stopStreamingProgressTimer, 'function');
        });

            })
})