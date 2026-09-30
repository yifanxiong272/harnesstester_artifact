let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.classifyFailoverReason', function() {
    const fn = testpilot_subject.file_0001.classifyFailoverReason;

    it('returns null for empty or whitespace-only strings', function() {
        assert.strictEqual(fn(''), null);
        assert.strictEqual(fn('   \n\t  '), null);
    });

    })