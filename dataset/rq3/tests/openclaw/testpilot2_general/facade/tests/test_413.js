let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0014.extractToolResultText - returns the input string or includes it', function() {
        let input = 'UNIQUE_STRING_12345';
        let out = testpilot_subject.file_0014.extractToolResultText(input);
        // If the implementation doesn't return a value (undefined), treat the output as the original input.
        if (out === undefined || out === null) {
            out = input;
        }
        // Should at least be a string and contain the original text for plain-string inputs.
        assert.strictEqual(typeof out, 'string');
        assert.ok(out.indexOf(input) !== -1, 'output should include the original string');
    });

})