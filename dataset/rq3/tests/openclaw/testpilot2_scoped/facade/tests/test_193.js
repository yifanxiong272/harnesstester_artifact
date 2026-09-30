let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('file_0007.createApplyPatchTool', function() {
        it('should export a function', function() {
            assert.ok(testpilot_subject);
            assert.strictEqual(typeof testpilot_subject.file_0007.createApplyPatchTool, 'function',
                'createApplyPatchTool should be a function');
        });

            })
})