let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0009.renderExecHostLabel', function() {
        it('returns "sandbox" when host is "sandbox"', function() {
            const result = testpilot_subject.file_0009.renderExecHostLabel("sandbox");
            assert.strictEqual(result, "sandbox");
        });

            })
})