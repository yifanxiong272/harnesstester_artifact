let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0003.ToolCallComponent.prototype.notifySnapshotChange', function() {
        it('should exist and be a function on the prototype', function() {
            assert.ok(testpilot_subject, 'module testpilot_subject is present');
            assert.ok(testpilot_subject.file_0003, 'namespace file_0003 is present');
            const ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
            assert.ok(ToolCallComponent, 'ToolCallComponent is present');
            assert.strictEqual(typeof ToolCallComponent.prototype.notifySnapshotChange, 'function',
                'notifySnapshotChange must be a function on the prototype');
        });

            })
})