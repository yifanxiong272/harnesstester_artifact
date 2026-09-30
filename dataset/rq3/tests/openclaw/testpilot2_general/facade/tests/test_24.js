let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.formatBillingErrorMessage', function() {
    it('returns provider + model when both are provided (no extra whitespace)', function() {
        const provider = 'OpenAI';
        const model = 'gpt-4';
        const actual = testpilot_subject.file_0001.formatBillingErrorMessage(provider, model);
        const expected = "\u26A0\uFE0F OpenAI (gpt-4) returned a billing error \u2014 your API key has run out of credits or has an insufficient balance. Check your OpenAI billing dashboard and top up or switch to a different API key.";
        assert.strictEqual(actual, expected);
    });

    })