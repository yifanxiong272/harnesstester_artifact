let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.formatRawAssistantErrorForUi', function() {
        it('returns a string and includes the input when given a plain string', function() {
            const input = 'simple error text';
            const out = testpilot_subject.file_0001.formatRawAssistantErrorForUi(input);
            assert.strictEqual(typeof out, 'string', 'output should be a string');
            assert.ok(out.includes(input), 'output should include the original string');
        });

            })
})