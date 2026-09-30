let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.formatBillingErrorMessage', function() {
        it('includes provider and model when both provided (and trims input)', function() {
            const provider = ' OpenAI ';
            const model = ' gpt-4 ';
            const out = testpilot_subject.file_0001.formatBillingErrorMessage(provider, model);
            const expected = '⚠️ OpenAI (gpt-4) returned a billing error — your API key has run out of credits or has an insufficient balance. Check your OpenAI billing dashboard and top up or switch to a different API key.';
            assert.strictEqual(out, expected);
        });

            })
})