let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0014.isToolResultError;

    it('returns false for non-object and falsy inputs', function() {
        assert.strictEqual(fn(null), false, 'null should be treated as not an error');
        assert.strictEqual(fn(undefined), false, 'undefined should be treated as not an error');
        assert.strictEqual(fn(0), false, 'number should be treated as not an error');
        assert.strictEqual(fn('error'), false, 'string should be treated as not an error');
        assert.strictEqual(fn(true), false, 'boolean should be treated as not an error');
    });

    })