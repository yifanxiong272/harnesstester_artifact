let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.getReadSnapshot', function() {
        it('returns pending snapshot when result is undefined and non-string file_path yields undefined filePath', function() {
            // create an instance without invoking constructor
            const inst = Object.create(testpilot_subject.file_0003.ToolCallComponent.prototype);
            inst.toolCall = { id: 'tc-pending-1', args: { file_path: null } }; // non-string file_path -> filePath should be undefined
            inst.workspaceDir = '/workspace/dir';
            inst.result = undefined;

            const snap = inst.getReadSnapshot();
            assert.strictEqual(snap.toolCallId, 'tc-pending-1');
            assert.strictEqual(snap.phase, 'pending');
            assert.strictEqual(snap.lines, 0);
            assert.strictEqual(snap.filePath, undefined);
        });

            })
})