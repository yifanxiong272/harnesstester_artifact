let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0013.convertToOpenAiMessages', function() {
    it('returns an empty array when given an empty array', function() {
        let input = [];
        let output = testpilot_subject.file_0013.convertToOpenAiMessages(input, {});
        assert(Array.isArray(output), 'output should be an array');
        assert.strictEqual(output.length, 0, 'output array should be empty');
    });

    })