let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0018.convertAnthropicMessageToGemini', function() {
        const subject = testpilot_subject.file_0018;
        const originalConvert = subject.convertAnthropicContentToGemini;

        afterEach(function() {
            // restore original implementation so tests are isolated
            subject.convertAnthropicContentToGemini = originalConvert;
        });

        it('returns empty array when convertAnthropicContentToGemini returns an empty array', function() {
            subject.convertAnthropicContentToGemini = function(content, options) {
                // should be invoked, but returns empty to trigger the early return
                return [];
            };

            const message = { role: 'assistant', content: ['ignored'] };
            const result = subject.convertAnthropicMessageToGemini(message, { someOpt: true });

            assert.deepStrictEqual(result, [], 'Expected empty array when parts are empty');
        });

            })
})