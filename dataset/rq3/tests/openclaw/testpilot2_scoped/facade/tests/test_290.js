let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0009.sanitizeToolCallId', function() {
    const fn = testpilot_subject.file_0009.sanitizeToolCallId;

    it('returns "defaulttoolid" for null/undefined/non-string in default (strict) mode', function() {
        assert.strictEqual(fn(null), "defaulttoolid");
        assert.strictEqual(fn(undefined), "defaulttoolid");
        assert.strictEqual(fn(12345), "defaulttoolid"); // non-string
    });

    })