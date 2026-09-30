let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports cleanupAfterTruncation as a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0004);
        assert.strictEqual(typeof testpilot_subject.file_0004.cleanupAfterTruncation, 'function');
    });

    })