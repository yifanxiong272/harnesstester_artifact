let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isBillingAssistantError', function() {

        it('returns a boolean for a variety of inputs', function() {
            const inputs = [
                undefined,
                null,
                '',
                'Billing Assistant error: quota exceeded',
                'some unrelated message',
                { message: 'Billing Assistant failed to authorize' },
                { code: 'BillingAssistantError' },
                new Error('Billing Assistant crash'),
                { nested: { text: 'billing' } }
            ];

            inputs.forEach((input) => {
                const result = testpilot_subject.file_0001.isBillingAssistantError(input);
                assert.strictEqual(typeof result, 'boolean', `expected boolean for input: ${String(input)}`);
            });
        });

            })
})