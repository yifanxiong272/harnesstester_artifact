let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0014.extractToolErrorMessage', function() {
    const fn = testpilot_subject.file_0014.extractToolErrorMessage;

    it('returns undefined for non-objects and null/undefined', function() {
        assert.strictEqual(fn(undefined), undefined);
        assert.strictEqual(fn(null), undefined);
        assert.strictEqual(fn('a string'), undefined);
        assert.strictEqual(fn(123), undefined);
    });

    })