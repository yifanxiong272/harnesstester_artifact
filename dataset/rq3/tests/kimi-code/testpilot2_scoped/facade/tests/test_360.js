let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper that calls cancelGoal and normalizes sync/async behavior into a Promise.
    async function callCancelGoal(instance, arg) {
        try {
            let ret = instance.cancelGoal(arg);
            // If it looks like a Promise, await it
            if (ret && typeof ret.then === 'function') {
                return await ret;
            }
            // sync successful return
            return ret;
        } catch (err) {
            // rethrow so callers can assert rejection
            throw err;
        }
    }

    it('should expose KimiCore and a cancelGoal function', function() {
        // basic existence checks
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should exist');
        let KimiCore = testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore should exist');
        assert.strictEqual(typeof KimiCore.prototype.cancelGoal, 'function', 'cancelGoal should be a function on the prototype');
    });

    })