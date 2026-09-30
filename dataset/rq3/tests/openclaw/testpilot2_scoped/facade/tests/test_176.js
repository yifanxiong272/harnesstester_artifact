let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0004.cleanSchemaForGemini;

    it('returns primitives unchanged (number, string, boolean)', function() {
        assert.strictEqual(fn(42), 42);
        assert.strictEqual(fn("hello"), "hello");
        assert.strictEqual(fn(false), false);
    });

    })