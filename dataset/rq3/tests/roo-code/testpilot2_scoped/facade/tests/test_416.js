let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const convert = testpilot_subject.file_0018.convertAnthropicMessageToGemini;

    it('basic conversion: preserves message text somewhere in the output and returns an object', function() {
        const message = { role: 'human', content: 'Hello world' };
        const before = JSON.parse(JSON.stringify(message)); // deep copy for mutation check

        const out = convert(message, {});
        // output should be an object (not null)
        assert.strictEqual(typeof out, 'object');
        assert.ok(out !== null);

        // original text should appear somewhere in the output when serialized
        assert.ok(JSON.stringify(out).includes('Hello world'));

        // function should not mutate the input
        assert.deepStrictEqual(message, before);
    });

    })