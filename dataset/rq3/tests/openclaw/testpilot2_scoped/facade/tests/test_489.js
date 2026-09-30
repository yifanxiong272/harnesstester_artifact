let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0017.appendBootstrapPromptWarning;

    it('returns original prompt when warningLines is undefined or empty', function() {
        const prompt = 'Original prompt';
        assert.strictEqual(fn(prompt, undefined, undefined), prompt, 'should return original prompt when warningLines undefined');
        assert.strictEqual(fn(prompt, [], undefined), prompt, 'should return original prompt when warningLines empty array');
    });

    })