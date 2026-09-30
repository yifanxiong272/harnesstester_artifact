let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to get the setPermission function from the prototype without running any constructor
    const KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
    it('has a setPermission function on the prototype', function() {
        assert.ok(KimiCore, 'KimiCore must exist on testpilot_subject.file_0002');
        assert.strictEqual(typeof KimiCore.prototype.setPermission, 'function', 'setPermission should be a function');
    });

    })