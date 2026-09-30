let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0002.KimiCore.prototype.undoHistory', function() {
    // Helper to detect a thenable/promise
    function isThenable(x) {
        return x && (typeof x.then === 'function');
    }

    it('should exist and be a function on the prototype', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        // drill down safely
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should exist');
        const KimiCoreProto = testpilot_subject.file_0002.KimiCore && testpilot_subject.file_0002.KimiCore.prototype;
        assert.ok(KimiCoreProto, 'KimiCore.prototype should exist');
        assert.strictEqual(typeof KimiCoreProto.undoHistory, 'function', 'undoHistory should be a function on the prototype');
    });

    })