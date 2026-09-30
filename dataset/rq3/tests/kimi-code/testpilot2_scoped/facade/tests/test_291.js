let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0002.KimiCore.prototype.getConfig - static inspections', function() {
    it('exports KimiCore with a getConfig method on its prototype', function() {
        // basic existence checks
        assert.ok(testpilot_subject, 'expected testpilot_subject to be present');
        assert.ok(testpilot_subject.file_0002, 'expected file_0002 to be present on testpilot_subject');
        const KimiCore = testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'expected KimiCore to be exported');
        assert.strictEqual(typeof KimiCore.prototype.getConfig, 'function', 'expected getConfig to be a function on the prototype');
    });

    })