let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0007.createApplyPatchTool', function() {
        it('returns a tool object with expected shape', function() {
            const tool = testpilot_subject.file_0007.createApplyPatchTool();
            assert.ok(tool && typeof tool === 'object', 'tool should be an object');
            assert.strictEqual(tool.name, 'apply_patch');
            assert.strictEqual(tool.label, 'apply_patch');
            assert.strictEqual(typeof tool.description, 'string');
            assert.ok(tool.parameters, 'tool should have parameters');
            assert.strictEqual(typeof tool.execute, 'function', 'tool.execute should be a function');
        });

            })
})