let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to detect a Promise
    function isPromise(obj) {
        return !!obj && (typeof obj === 'object' || typeof obj === 'function') && typeof obj.then === 'function';
    }

    it('test testpilot_subject.file_0002.KimiCore.prototype.listSkills - should exist and be a function', function() {
        // navigate safely to the prototype function
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        let KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore constructor should exist on testpilot_subject.file_0002');
        assert.strictEqual(typeof KimiCore.prototype.listSkills, 'function', 'listSkills should be a function on KimiCore.prototype');
    });

    })