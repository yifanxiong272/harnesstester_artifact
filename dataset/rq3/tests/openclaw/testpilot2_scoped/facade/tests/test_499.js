let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('formatBootstrapTruncationWarningLines should be a function', function() {
        assert.strictEqual(typeof testpilot_subject.file_0017.formatBootstrapTruncationWarningLines, 'function');
    });

    })