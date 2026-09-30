let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0002.OutputManager.prototype.getCurrentlyStreamingTs', function() {

    // Helper to create an instance (or an object inheriting the prototype)
    function makeInstance() {
        const container = testpilot_subject && testpilot_subject.file_0002;
        if (!container) throw new Error('testpilot_subject.file_0002 not found in module');
        const OutputManager = container.OutputManager;
        if (!OutputManager) throw new Error('OutputManager not found on testpilot_subject.file_0002');

        // Try to instantiate normally; if constructor requires args or throws, fall back to object with prototype
        try {
            return new OutputManager();
        } catch (e) {
            // fall back to an object that inherits the prototype so we can call the method
            return Object.create(OutputManager.prototype);
        }
    }

    it('should expose getCurrentlyStreamingTs as a function on the prototype', function() {
        const container = testpilot_subject && testpilot_subject.file_0002;
        assert.ok(container, 'testpilot_subject.file_0002 must exist');
        const OutputManager = container.OutputManager;
        assert.ok(OutputManager, 'OutputManager must exist');
        assert.strictEqual(typeof OutputManager.prototype.getCurrentlyStreamingTs, 'function',
            'getCurrentlyStreamingTs should be a function on OutputManager.prototype');
    });

    })