let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0008.normalizePathPrepend', function() {
    it('returns [] for non-array inputs', function() {
        const fn = testpilot_subject.file_0008.normalizePathPrepend;
        assert.deepStrictEqual(fn(undefined), []);
        assert.deepStrictEqual(fn(null), []);
        assert.deepStrictEqual(fn(123), []);
        assert.deepStrictEqual(fn({}), []);
        assert.deepStrictEqual(fn('a string'), []);
    });

    })