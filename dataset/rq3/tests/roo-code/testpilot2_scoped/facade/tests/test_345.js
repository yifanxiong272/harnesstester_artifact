let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0014.TagMatcher.prototype.pop - exists as a function', function() {
        assert.ok(testpilot_subject);
        let TagMatcher = testpilot_subject.file_0014 && testpilot_subject.file_0014.TagMatcher;
        assert.ok(TagMatcher, 'TagMatcher class should exist at testpilot_subject.file_0014.TagMatcher');
        assert.strictEqual(typeof TagMatcher.prototype.pop, 'function', 'TagMatcher.prototype.pop should be a function');
    });

    })