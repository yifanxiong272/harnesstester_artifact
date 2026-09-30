let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    const fn = testpilot_subject.file_0003 && testpilot_subject.file_0003.sanitizeToolCallInputs;
    it('is available as a function', function() {
        assert.ok(fn, 'sanitizeToolCallInputs should be exported');
        assert.strictEqual(typeof fn, 'function');
    });

    })