let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.classifyFailoverReason', function() {
    it('returns null for empty or whitespace-only input', function() {
        assert.strictEqual(typeof testpilot_subject.file_0001.classifyFailoverReason, 'function', 'classifyFailoverReason should be a function');
        assert.strictEqual(testpilot_subject.file_0001.classifyFailoverReason(''), null);
        assert.strictEqual(testpilot_subject.file_0001.classifyFailoverReason('   \n\t  '), null);
    });

    })