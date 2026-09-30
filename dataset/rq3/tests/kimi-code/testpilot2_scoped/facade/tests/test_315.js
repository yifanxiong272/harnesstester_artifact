let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('has the getMcpStartupMetrics method on the prototype', function() {
        let KimiCore = testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore must be present');
        assert.strictEqual(typeof KimiCore.prototype.getMcpStartupMetrics, 'function',
            'getMcpStartupMetrics should be a function on the prototype');
    });

    // Helper to call the method and normalize sync / promise results
    async function invokeMaybeAsync(fn, arg) {
        let res = fn(arg);
        if (res && typeof res.then === 'function') {
            return await res;
        }
        return res;
    }

    })