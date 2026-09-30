let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCoreProto = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore && testpilot_subject.file_0002.KimiCore.prototype;
    it('KimiCore.prototype.cancelCompaction should exist and be a function', function() {
        assert(KimiCoreProto, 'KimiCore prototype is not present on testpilot_subject.file_0002');
        assert.strictEqual(typeof KimiCoreProto.cancelCompaction, 'function', 'cancelCompaction is not a function');
    });

    })