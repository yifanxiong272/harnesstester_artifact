let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0026.ToolInputSchema.parse', function() {
    it('should export a parse function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should exist');
        assert.ok(testpilot_subject.file_0026, 'module should contain file_0026');
        assert.ok(testpilot_subject.file_0026.ToolInputSchema, 'file_0026 should contain ToolInputSchema');
        assert.strictEqual(
            typeof testpilot_subject.file_0026.ToolInputSchema.parse,
            'function',
            'ToolInputSchema.parse should be a function'
        );
    });

    })