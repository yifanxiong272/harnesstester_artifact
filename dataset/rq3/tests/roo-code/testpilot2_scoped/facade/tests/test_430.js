let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0020.mergeEnvironmentDetailsForMiniMax;

    it('preserves non-user messages and user string content', function() {
        const messages = [
            { role: 'system', content: 'system message' },
            { role: 'user', content: 'a plain user string' },
            { role: 'assistant', content: { some: 'object' } }
        ];
        const out = fn(messages);
        assert.deepStrictEqual(out, messages);
    });

    })