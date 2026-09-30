let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0008.OpenAICompatibleHandler.prototype.completePrompt', function() {

        it('rejects when no suitable client method is available', async function() {
            const proto = testpilot_subject.file_0008.OpenAICompatibleHandler.prototype;
            const handler = Object.create(proto);

            // client present but does not implement supported methods
            handler.client = {};

            let threw = false;
            try {
                await handler.completePrompt('anything');
            } catch (err) {
                threw = true;
                // Expect some kind of error, message/content may vary by implementation
                assert.ok(err instanceof Error, 'should reject with an Error when no method is available');
            }
            assert.strictEqual(threw, true, 'completePrompt should reject if neither createChatCompletion nor createCompletion exist');
        });

    });
});