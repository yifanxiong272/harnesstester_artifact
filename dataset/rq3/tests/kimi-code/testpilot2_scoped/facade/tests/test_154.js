let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case the implementation uses some internal delays
    this.timeout(5000);

    it('test testpilot_subject.file_0002.KimiCore.prototype.getConfigDiagnostics exists and is callable', function() {
        assert.ok(testpilot_subject, 'testpilot_subject should be available');
        const KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore constructor should exist');
        assert.ok(
            typeof KimiCore.prototype.getConfigDiagnostics === 'function',
            'getConfigDiagnostics should be a function on the prototype'
        );
    });

    })