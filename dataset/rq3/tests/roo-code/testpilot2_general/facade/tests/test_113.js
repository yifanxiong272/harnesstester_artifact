let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const OutputManager = testpilot_subject.file_0002.OutputManager;

    it('should have isCurrentlyStreaming as a function on the prototype', function() {
        assert.strictEqual(typeof OutputManager.prototype.isCurrentlyStreaming, 'function');
    });

    })