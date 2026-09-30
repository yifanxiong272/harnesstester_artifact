let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.isCompactionFailureError', function() {
    const fn = testpilot_subject && testpilot_subject.file_0001 && testpilot_subject.file_0001.isCompactionFailureError;
    it('should be a function', function() {
        assert.strictEqual(typeof fn, 'function');
    });

    })