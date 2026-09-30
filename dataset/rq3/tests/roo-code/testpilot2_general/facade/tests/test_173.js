let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0004.PromptManager.prototype.promptForYesNo', function() {

        it('returns true for "y" and "yes" (case-insensitive, trimmed)', async function() {
            const pm = Object.create(testpilot_subject.file_0004.PromptManager.prototype);
            pm.promptForInput = async function(prompt) {
                // simulate user entering a value with surrounding whitespace and mixed case
                return '  YeS  ';
            };

            const result = await pm.promptForYesNo('unused prompt');
            assert.strictEqual(result, true);
        });

            })
})