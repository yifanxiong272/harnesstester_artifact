let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;

    it('exports KimiCore as a constructor/function', function() {
        assert.ok(KimiCore, 'KimiCore should be exported');
        assert.strictEqual(typeof KimiCore, 'function', 'KimiCore should be a function (constructor)');
    });

    })