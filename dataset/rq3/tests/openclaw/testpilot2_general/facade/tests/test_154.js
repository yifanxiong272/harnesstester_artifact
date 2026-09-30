let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.sanitizeUserFacingText;

    it('returns falsy inputs as-is (null, undefined, empty string)', function() {
        assert.strictEqual(fn(null), null);
        assert.strictEqual(fn(undefined), undefined);
        // empty string is falsy and per implementation should be returned as-is
        assert.strictEqual(fn(''), '');
    });

    })