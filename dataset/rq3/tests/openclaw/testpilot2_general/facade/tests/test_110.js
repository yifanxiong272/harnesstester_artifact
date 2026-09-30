let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should export isMissingToolCallInputError as a function', function() {
        assert.ok(testpilot_subject);
        assert.strictEqual(typeof testpilot_subject.file_0001.isMissingToolCallInputError, 'function');
    });

    })