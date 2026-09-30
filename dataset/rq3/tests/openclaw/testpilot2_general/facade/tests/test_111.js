let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const subject = testpilot_subject.file_0001;
    const fn = subject.isMissingToolCallInputError;

    it('is a function', function() {
        assert.strictEqual(typeof fn, 'function');
    });

    })