let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('returns an empty array when given an empty array', function() {
        let res = testpilot_subject.file_0003.stripToolResultDetails([]);
        assert.ok(Array.isArray(res), 'result should be an array');
        assert.strictEqual(res.length, 0);
    });

    })