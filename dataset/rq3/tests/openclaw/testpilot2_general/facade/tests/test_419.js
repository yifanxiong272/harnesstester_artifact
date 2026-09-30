let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0014;

    it('testpilot_subject.file_0014.isToolResultMediaTrusted should return false for falsy toolName', function() {
        // falsy toolName values should all return false regardless of result
        assert.strictEqual(fn.isToolResultMediaTrusted(undefined, {}), false);
        assert.strictEqual(fn.isToolResultMediaTrusted(null, {}), false);
        assert.strictEqual(fn.isToolResultMediaTrusted('', {}), false);
    });

    })