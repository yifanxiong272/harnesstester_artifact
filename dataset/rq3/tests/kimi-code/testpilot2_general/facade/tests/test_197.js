let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.buildHeader', function() {
        const proto = testpilot_subject &&
                      testpilot_subject.file_0003 &&
                      testpilot_subject.file_0003.ToolCallComponent &&
                      testpilot_subject.file_0003.ToolCallComponent.prototype;

        it('exists and is a function', function() {
            assert.ok(proto, 'ToolCallComponent prototype is available');
            assert.strictEqual(typeof proto.buildHeader, 'function', 'buildHeader should be a function');
        });

            })
})