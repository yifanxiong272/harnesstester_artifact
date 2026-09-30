let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const TagMatcher = testpilot_subject.file_0014.TagMatcher;

    it('should return a single unmatched chunk for plain text', function(done) {
        const tm = new TagMatcher('a', null);
        const res = tm.update("hello");
        assert.deepStrictEqual(res, [{ data: "hello", matched: false }]);
        done();
    });

    })