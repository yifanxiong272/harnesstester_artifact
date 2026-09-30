let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // allow a bit more time for timer-based tests on slower CI
    this.timeout(5000);

    const protoPath = (() => {
        // safe navigation in case some intermediate objects are missing
        if (!testpilot_subject) return null;
        if (!testpilot_subject.file_0003) return null;
        if (!testpilot_subject.file_0003.ToolCallComponent) return null;
        return testpilot_subject.file_0003.ToolCallComponent.prototype;
    })();

    it('ToolCallComponent.prototype.stopSubagentElapsedTimer should exist and be a function', function() {
        assert.ok(protoPath, 'Expected testpilot_subject.file_0003.ToolCallComponent.prototype to exist');
        assert.strictEqual(typeof protoPath.stopSubagentElapsedTimer, 'function',
            'stopSubagentElapsedTimer should be a function on the prototype');
    });

    })