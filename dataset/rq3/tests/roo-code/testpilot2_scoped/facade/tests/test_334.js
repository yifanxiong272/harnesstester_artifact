let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('file_0013.consolidateReasoningDetails should be a function', function() {
        assert.strictEqual(
            typeof testpilot_subject.file_0013.consolidateReasoningDetails,
            'function',
            'consolidateReasoningDetails should be a function'
        );
    });

    })