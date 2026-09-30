let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const writeFn = testpilot_subject.file_0004.PromptManager.prototype.write;

    it('calls stdout.write with the provided text (string)', function() {
        let recorded = [];
        const fakeStdout = {
            write: function(text) {
                recorded.push(text);
            }
        };
        writeFn.call({ stdout: fakeStdout }, 'hello world');
        assert.strictEqual(recorded.length, 1);
        assert.strictEqual(recorded[0], 'hello world');
    });

    })