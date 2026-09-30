let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0001.isContextOverflowError - returns false for unrelated messages and empty string', function(done) {
        let fn = testpilot_subject.file_0001.isContextOverflowError;

        let unrelated = 'Out of memory';
        assert.strictEqual(fn(unrelated), false, 'unrelated error messages should not be recognized as context overflow');

        let empty = '';
        assert.strictEqual(fn(empty), false, 'empty string should not be treated as context overflow');

        done();
    });
});