let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const TagMatcher = testpilot_subject.file_0014 && testpilot_subject.file_0014.TagMatcher;

    it('pop returns stored chunks and clears chunks when transform is falsy', function() {
        const tm = new TagMatcher();
        // set up chunks and no transform
        const original = [1, 2, 3];
        tm.chunks = original;
        tm.transform = undefined;

        const popped = tm.pop();

        // returns the original chunk array
        assert.deepStrictEqual(popped, original);

        // chunks should be cleared to a new empty array
        assert.deepStrictEqual(tm.chunks, []);
        assert.notStrictEqual(tm.chunks, original); // not the same reference
    });

    })