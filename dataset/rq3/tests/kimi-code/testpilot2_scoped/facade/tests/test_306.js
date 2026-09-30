let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call updateSessionMetadata and handle sync/async returns
    function callUpdate(fn, thisArg, arg) {
        try {
            const res = fn.call(thisArg, arg);
            if (res && typeof res.then === 'function') {
                return res;
            }
            return Promise.resolve(res);
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('should expose updateSessionMetadata as a function on the prototype', function() {
        assert.ok(testpilot_subject);
        // navigate safely to the method
        const KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore constructor should exist at testpilot_subject.file_0002.KimiCore');
        assert.strictEqual(typeof KimiCore.prototype.updateSessionMetadata, 'function',
            'updateSessionMetadata should be a function on the prototype');
    });

    })