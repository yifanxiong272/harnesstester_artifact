let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0013.convertToOpenAiMessages', function() {
        const convert = testpilot_subject.file_0013.convertToOpenAiMessages;

        it('passes through simple string messages unchanged (role and content)', function() {
            const anthropic = [
                { role: 'user', content: 'hello user' },
                { role: 'assistant', content: 'hello assistant' }
            ];
            const out = convert(anthropic, {});
            assert.deepStrictEqual(out, [
                { role: 'user', content: 'hello user' },
                { role: 'assistant', content: 'hello assistant' }
            ]);
        });

            })
})