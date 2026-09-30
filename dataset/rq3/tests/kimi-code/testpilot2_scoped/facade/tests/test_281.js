let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.KimiCore.prototype.getBackgroundOutput - method exists', function() {
        assert(testpilot_subject, 'module testpilot_subject should be require-able');
        const KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        assert(typeof KimiCore === 'function', 'KimiCore should be a constructor function');
        assert(typeof KimiCore.prototype.getBackgroundOutput === 'function', 'getBackgroundOutput should exist on the prototype');
    });

    // Helper to call the method and normalize sync/async returns into a Promise
    function callGetBackgroundOutput(instance, input) {
        try {
            const res = instance.getBackgroundOutput(input);
            if (res && typeof res.then === 'function') {
                // result is a Promise
                return res;
            }
            // normalize synchronous result to a resolved Promise
            return Promise.resolve(res);
        } catch (err) {
            return Promise.reject(err);
        }
    }

    })