let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper
    function isPromise(x) {
        return !!x && (typeof x.then === 'function');
    }
    function toPromise(x) {
        return isPromise(x) ? x : Promise.resolve(x);
    }

    it('KimiCore.prototype.cancel should exist and be a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should be present');
        assert.ok(testpilot_subject.file_0002.KimiCore, 'KimiCore should be present');
        assert.strictEqual(typeof testpilot_subject.file_0002.KimiCore.prototype.cancel, 'function',
            'KimiCore.prototype.cancel should be a function');
    });

    })