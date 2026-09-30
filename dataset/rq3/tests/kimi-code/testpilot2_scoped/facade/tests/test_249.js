let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.KimiCore.prototype.clearPlan - exists and is a function', function() {
        const KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore should be exported under testpilot_subject.file_0002.KimiCore');
        assert.strictEqual(typeof KimiCore.prototype.clearPlan, 'function', 'clearPlan should be a function on the prototype');
    });

    })