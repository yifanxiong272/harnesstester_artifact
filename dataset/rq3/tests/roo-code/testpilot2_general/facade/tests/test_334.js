let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0007.isValidExtensionMessage;

    it('should return false for null and undefined', function() {
        assert.strictEqual(fn(null), false);
        assert.strictEqual(fn(undefined), false);
    });

    })