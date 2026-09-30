let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    let KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;

    it('KimiCore.prototype.getKimiConfig should be a function', function() {
        assert.ok(KimiCore, 'KimiCore class is present on testpilot_subject.file_0002');
        assert.strictEqual(typeof KimiCore.prototype.getKimiConfig, 'function', 'getKimiConfig should be a function on the prototype');
    });

    })