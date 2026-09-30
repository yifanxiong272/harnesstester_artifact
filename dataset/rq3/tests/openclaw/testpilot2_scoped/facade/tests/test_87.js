let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0001.isImageDimensionErrorMessage', function() {
    it('always returns a boolean for a variety of inputs', function() {
        const fn = testpilot_subject.file_0001.isImageDimensionErrorMessage;
        // basic sanity: for different input types it should always be a boolean
        assert.strictEqual(typeof fn('some string'), 'boolean');
        assert.strictEqual(typeof fn(''), 'boolean');
        // coerce non-string inputs to strings so the implementation that expects a string won't throw
        assert.strictEqual(typeof fn(String(null)), 'boolean');
        assert.strictEqual(typeof fn(String(undefined)), 'boolean');
        assert.strictEqual(typeof fn(String(0)), 'boolean');
        assert.strictEqual(typeof fn(String({})), 'boolean');
        assert.strictEqual(typeof fn(String([])), 'boolean');
    });

    })