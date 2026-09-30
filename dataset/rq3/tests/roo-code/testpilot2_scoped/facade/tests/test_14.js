let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const convert = testpilot_subject.file_0004.convertToolBlocksToText;

    it('returns the input unchanged when given a string', function() {
        const input = "just a plain string";
        const output = convert(input);
        assert.strictEqual(output, input);
    });

    })