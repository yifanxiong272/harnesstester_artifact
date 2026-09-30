let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('file_0009.normalizeNotifyOutput', function() {
        const fn = testpilot_subject.file_0009.normalizeNotifyOutput;

        it('collapses multiple spaces to single space and trims ends', function() {
            const input = '   hello    world   this   is   a   test   ';
            const expected = 'hello world this is a test';
            assert.strictEqual(fn(input), expected);
        });

            })
})