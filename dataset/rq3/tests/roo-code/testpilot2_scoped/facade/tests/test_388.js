let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0016.FakeAIHandler.prototype.countTokens', function() {
        it('forwards string content to this.ai.countTokens and returns its result', function() {
            // Create an object that uses the real prototype but with a controlled `ai`.
            const handler = Object.create(testpilot_subject.file_0016.FakeAIHandler.prototype);
            let received = null;
            handler.ai = {
                countTokens: function(content) {
                    received = content;
                    return 42;
                }
            };

            const result = handler.countTokens('hello world');
            assert.strictEqual(received, 'hello world', 'content should be forwarded unchanged');
            assert.strictEqual(result, 42, 'return value should be whatever ai.countTokens returns');
        });

            })
})