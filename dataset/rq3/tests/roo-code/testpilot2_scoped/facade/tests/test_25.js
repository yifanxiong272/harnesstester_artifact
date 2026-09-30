let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0004.summarizeConversation', function() {
    const summarize = testpilot_subject.file_0004.summarizeConversation;

    it('returns an error when there are not enough messages to condense (<= 1)', async function() {
        const messages = [{ role: 'user', content: 'hello', ts: 1 }];

        const result = await summarize({
            messages
            // other options intentionally omitted to exercise early-return path
        });

        // Early-return should preserve the original messages reference
        assert.strictEqual(result.messages, messages);
        assert.strictEqual(result.cost, 0);
        assert.strictEqual(result.summary, "");
        assert.ok(result.error, "Expected an error message when not enough messages to condense");
    });

    })