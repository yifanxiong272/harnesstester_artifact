let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0017.convertToMistralMessages', function() {
    const convert = testpilot_subject.file_0017.convertToMistralMessages;

    it('passes through messages whose content is a string', function() {
        const input = [
            { role: 'system', content: 'System initialization' },
            { role: 'user', content: 'Plain user string' }
        ];
        const out = convert(input);
        assert.deepStrictEqual(out, [
            { role: 'system', content: 'System initialization' },
            { role: 'user', content: 'Plain user string' }
        ]);
    });

    })