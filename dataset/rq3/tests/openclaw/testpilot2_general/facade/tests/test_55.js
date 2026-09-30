let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.isBillingErrorMessage;

    it('returns false for empty string', function() {
        assert.strictEqual(fn(''), false);
    });

    })