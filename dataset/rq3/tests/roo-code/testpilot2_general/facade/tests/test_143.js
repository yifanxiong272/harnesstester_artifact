let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.OutputManager.prototype.outputSayMessage - existence and signature', function() {
        // Ensure the class and method exist and have the expected parameter count
        assert.ok(testpilot_subject, 'module "testpilot_subject" should be present');
        assert.ok(testpilot_subject.file_0002, 'module should expose file_0002');
        const OutputManager = testpilot_subject.file_0002.OutputManager;
        assert.ok(OutputManager, 'OutputManager should be present in file_0002');
        assert.strictEqual(typeof OutputManager.prototype.outputSayMessage, 'function',
            'outputSayMessage should be a function on the prototype');
        // The function is expected to take six parameters (as per the signature given)
        assert.strictEqual(OutputManager.prototype.outputSayMessage.length, 6,
            'outputSayMessage should be declared with 6 parameters');
    });

    })