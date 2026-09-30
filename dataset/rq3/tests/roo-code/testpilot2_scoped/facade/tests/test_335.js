let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0013.consolidateReasoningDetails', function() {
    it('returns empty array for null/undefined/empty input', function(done) {
        const fn = testpilot_subject.file_0013.consolidateReasoningDetails;
        assert.deepStrictEqual(fn(undefined), []);
        assert.deepStrictEqual(fn(null), []);
        assert.deepStrictEqual(fn([]), []);
        done();
    });

    })