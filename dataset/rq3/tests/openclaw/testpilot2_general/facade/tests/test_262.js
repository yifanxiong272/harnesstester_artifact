let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0009.normalizePathPrepend;

    it('returns empty array for non-array inputs', function() {
        const nonArrays = [undefined, null, 123, "string", {a:1}, true];
        for (const val of nonArrays) {
            assert.deepStrictEqual(fn(val), [], `expected [] for input: ${String(val)}`);
        }
    });

    })