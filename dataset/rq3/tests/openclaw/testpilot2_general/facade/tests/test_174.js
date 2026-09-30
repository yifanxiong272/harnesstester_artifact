let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0004.cleanSchemaForGemini;

    it('returns non-object values unchanged (null, undefined, number, string, boolean)', function() {
        // primitives and null/undefined should be returned as-is
        assert.strictEqual(fn(null), null);
        assert.strictEqual(fn(undefined), undefined);
        assert.strictEqual(fn(123), 123);
        assert.strictEqual(fn('hello'), 'hello');
        assert.strictEqual(fn(true), true);
        assert.strictEqual(fn(false), false);
    });

    })