let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0014.TagMatcher.prototype.final', function() {
        it('should exist and be a function with arity 1', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0014, 'file_0014 namespace missing');
            assert.ok(testpilot_subject.file_0014.TagMatcher, 'TagMatcher missing');
            assert.strictEqual(typeof testpilot_subject.file_0014.TagMatcher.prototype.final, 'function');
            // Expect one declared argument (API suggests final(chunk))
            assert.strictEqual(testpilot_subject.file_0014.TagMatcher.prototype.final.length, 1);
        });

            })
})