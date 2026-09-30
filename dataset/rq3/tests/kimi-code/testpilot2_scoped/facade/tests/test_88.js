let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Allow a little extra time in case createSession does something slightly slow
    this.timeout(5000);

    it('KimiCore class and createSession method exist', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');

        // Navigate to the KimiCore class
        const file0002 = testpilot_subject.file_0002;
        assert.ok(file0002, 'file_0002 should be present on testpilot_subject');

        const KimiCore = file0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore should be present on file_0002');

        // The method should be available on the prototype
        assert.ok(
            typeof KimiCore.prototype.createSession === 'function',
            'KimiCore.prototype.createSession should be a function'
        );
    });

    })