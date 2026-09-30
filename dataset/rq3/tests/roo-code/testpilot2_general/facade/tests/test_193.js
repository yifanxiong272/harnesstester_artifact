let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0004.PromptManager.prototype.writeLine', function() {
        it('writes the given string followed by a newline to stdout', function() {
            // create an object with the PromptManager prototype but without running any constructor
            const pm = Object.create(testpilot_subject.file_0004.PromptManager.prototype);

            // capture writes
            const captured = [];
            pm.stdout = {
                write: function(s) { captured.push(s); }
            };

            const ret = pm.writeLine('hello world');

            assert.strictEqual(captured.length, 1);
            assert.strictEqual(captured[0], 'hello world\n');
            // function does not return anything (undefined)
            assert.strictEqual(ret, undefined);
        });

            })
})