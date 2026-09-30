let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0001.classifyFailoverReason', function() {
    // Short helper to call the function under test
    const classify = (s) => {
        return testpilot_subject.file_0001.classifyFailoverReason(s);
    };

    it('returns null for empty string', function() {
        assert.strictEqual(classify(""), null);
    });

    })