let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0017.normalizeMistralToolCallId', function() {
        const fn = testpilot_subject.file_0017.normalizeMistralToolCallId;

        it('is exported as a function', function() {
            assert.strictEqual(typeof fn, 'function', 'normalizeMistralToolCallId should be a function');
        });

            })
})