let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

// Ensure atob is available in Node for base64 decoding (the function under test uses atob)
if (typeof global.atob === 'undefined') {
    global.atob = (b64) => Buffer.from(b64, 'base64').toString('binary');
}

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0005.convertToBedrockConverseMessages;

    it('converts simple string assistant message to bedrock format', function() {
        const anthropic = [{ role: 'assistant', content: 'hello world' }];
        const out = fn(anthropic);
        assert.strictEqual(out.length, 1);
        assert.strictEqual(out[0].role, 'assistant');
        assert.deepStrictEqual(out[0].content, [{ text: 'hello world' }]);
    });

    })