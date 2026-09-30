let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const Proto = testpilot_subject.file_0003.ToolCallComponent.prototype;

    it('backgroundTaskTerminalPhase takes precedence over other indicators', function() {
        const obj = Object.create(Proto);
        // Even though other flags are set, backgroundTaskTerminalPhase should win.
        obj.backgroundTaskTerminalPhase = 'terminal-phase';
        obj.detachedFromForeground = true;
        obj.subagentPhase = 'backgrounded';
        obj.result = { is_error: true };
        assert.strictEqual(obj.getDerivedSubagentPhase(), 'terminal-phase');
    });

    })