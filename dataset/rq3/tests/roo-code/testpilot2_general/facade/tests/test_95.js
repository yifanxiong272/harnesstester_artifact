let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const OutputManager = testpilot_subject.file_0002 && testpilot_subject.file_0002.OutputManager;

    it('OutputManager should be available and outputMessage should be a function', function() {
        assert.ok(OutputManager, 'OutputManager class is not exported at testpilot_subject.file_0002.OutputManager');
        assert.strictEqual(typeof OutputManager.prototype.outputMessage, 'function',
            'outputMessage is not a function on OutputManager.prototype');
    });

    })