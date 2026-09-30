let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0009.formatExecFailureReason;

    it('should be a function', function() {
        assert.strictEqual(typeof fn, 'function');
    });

    })