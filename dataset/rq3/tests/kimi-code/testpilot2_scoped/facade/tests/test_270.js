let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.KimiCore.prototype.setActiveTools - exists and is a function', function() {
        assert.ok(testpilot_subject.file_0002, 'module.file_0002 should exist');
        const KimiCore = testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore should exist on file_0002');
        assert.strictEqual(typeof KimiCore.prototype.setActiveTools, 'function', 'setActiveTools should be a function');
    });

    })