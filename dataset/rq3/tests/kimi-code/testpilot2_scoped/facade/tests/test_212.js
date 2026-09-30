let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to uniformly handle sync/async returns
    function waitForResult(res) {
        if (res && typeof res.then === 'function') {
            return res;
        }
        return Promise.resolve(res);
    }

    it('test testpilot_subject.file_0002.KimiCore.prototype.setThinking exists', function() {
        // Ensure the class and method exist
        assert.ok(testpilot_subject);
        const KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        assert.ok(typeof KimiCore === 'function', 'KimiCore should be a constructor/function');
        assert.ok(typeof KimiCore.prototype.setThinking === 'function', 'setThinking should be a function on the prototype');
    });

    })