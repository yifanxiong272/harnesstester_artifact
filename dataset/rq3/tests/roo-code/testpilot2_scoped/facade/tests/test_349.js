let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0014.TagMatcher.prototype.update', function() {
    it('exposes a TagMatcher constructor and an update method on its prototype', function() {
        assert.ok(testpilot_subject, 'testpilot_subject should be require-able');

        let TagMatcher = testpilot_subject.file_0014 && testpilot_subject.file_0014.TagMatcher;
        assert.ok(TagMatcher, 'TagMatcher constructor should exist at file_0014.TagMatcher');
        assert.strictEqual(typeof TagMatcher, 'function', 'TagMatcher should be a function/constructor');

        // The prototype should have an update method
        assert.strictEqual(typeof TagMatcher.prototype.update, 'function', 'TagMatcher.prototype.update should be a function');
    });

    })