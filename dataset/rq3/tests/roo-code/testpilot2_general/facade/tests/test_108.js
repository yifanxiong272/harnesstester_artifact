let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const OutputManager = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.OutputManager;

    it('OutputManager and writeRaw should exist', function() {
        assert.ok(OutputManager, 'Expected testpilot_subject.file_0002.OutputManager to exist');
        assert.strictEqual(typeof OutputManager.prototype.writeRaw, 'function', 'Expected writeRaw to be a function on the prototype');
    });

    })