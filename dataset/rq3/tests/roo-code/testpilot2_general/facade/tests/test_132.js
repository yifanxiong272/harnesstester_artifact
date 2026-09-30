let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to obtain an instance of OutputManager if possible, otherwise a plain object with the prototype.
    function makeOutputManagerInstance() {
        const OM = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.OutputManager;
        if (!OM) return null;
        let inst = null;
        // Try a few constructor invocation strategies; many real constructors accept no args,
        // some require args, so fall back to creating an object with the prototype.
        try {
            inst = new OM();
            return inst;
        } catch (e1) {
            try {
                inst = new OM(undefined);
                return inst;
            } catch (e2) {
                // Last resort: create an object with the prototype but don't run the constructor.
                inst = Object.create(OM.prototype);
                return inst;
            }
        }
    }

    it('should have hasLoggedFirstPartial on the prototype and it should be a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject module is present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace is present');
        const OM = testpilot_subject.file_0002.OutputManager;
        assert.ok(OM, 'OutputManager exists');
        assert.strictEqual(typeof OM.prototype.hasLoggedFirstPartial, 'function', 'hasLoggedFirstPartial should be a function on the prototype');
    });

    })