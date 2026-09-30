let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.isLikelyContextOverflowError;

    it('should export a function', function() {
        assert.strictEqual(typeof fn, 'function', 'isLikelyContextOverflowError should be a function');
    });

    })