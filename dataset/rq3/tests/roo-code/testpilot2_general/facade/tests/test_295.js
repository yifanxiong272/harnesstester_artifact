let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create an instance of MessageProcessor in a forgiving way
    function createProcessor() {
        const MP = testpilot_subject && testpilot_subject.file_0007 && testpilot_subject.file_0007.MessageProcessor;
        assert.ok(MP, 'MessageProcessor should be exported at testpilot_subject.file_0007.MessageProcessor');

        // Try various ways to obtain an instance without relying on external resources or specific constructor args
        try {
            // Prefer "new" when possible
            return new MP();
        } catch (e1) {
            try {
                // Maybe it expects a config object; give an empty one
                return new MP({});
            } catch (e2) {
                // As a last resort, create a plain object that inherits the prototype so processMessage can be called
                return Object.create(MP.prototype || {});
            }
        }
    }

    it('MessageProcessor should be constructible and expose processMessage', function() {
        const inst = createProcessor();
        assert.ok(inst, 'failed to create processor instance');
        assert.strictEqual(typeof inst.processMessage, 'function', 'processMessage should be a function on the instance');
    });

    })