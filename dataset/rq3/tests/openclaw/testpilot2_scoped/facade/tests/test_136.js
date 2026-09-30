let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.parseApiErrorInfo', function() {
        const parse = testpilot_subject.file_0001.parseApiErrorInfo;

        it('returns null for null/undefined input', function() {
            assert.strictEqual(parse(null), null);
            assert.strictEqual(parse(undefined), null);
        });

            })
})