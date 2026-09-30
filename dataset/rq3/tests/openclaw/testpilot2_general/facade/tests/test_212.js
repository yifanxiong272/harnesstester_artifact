let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0008.createApplyPatchTool', function() {
    it('should be a function', function() {
        assert.strictEqual(
            typeof testpilot_subject.file_0008.createApplyPatchTool,
            'function',
            'createApplyPatchTool should be a function'
        );
    });

    })