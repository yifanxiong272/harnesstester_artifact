let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.isModelNotFoundErrorMessage;

    it('returns true for the exact message "Model not found"', function() {
        const raw = 'Model not found';
        const res = fn(raw);
        assert.strictEqual(res, true, 'Expected true for exact "Model not found" message');
    });

    })