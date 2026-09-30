let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call getPlan and normalize return to a Promise
    function callGetPlan(instance, arg) {
        try {
            const ret = instance.getPlan(arg);
            // If it looks like a Promise
            if (ret && typeof ret.then === 'function') {
                return ret;
            }
            // Otherwise wrap sync return in a resolved promise
            return Promise.resolve(ret);
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('has getPlan function on prototype', function() {
        assert(testpilot_subject.file_0002, 'file_0002 namespace missing');
        const proto = testpilot_subject.file_0002.KimiCore && testpilot_subject.file_0002.KimiCore.prototype;
        assert(proto, 'KimiCore.prototype missing');
        assert.strictEqual(typeof proto.getPlan, 'function', 'getPlan should be a function');
    });

    })