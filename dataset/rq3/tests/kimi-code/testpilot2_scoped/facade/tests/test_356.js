let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call pauseGoal and normalize sync/async results into a Promise
    function callPauseGoal(instance, payload) {
        return new Promise((resolve, reject) => {
            try {
                let res = instance.pauseGoal(payload);
                if (res && typeof res.then === 'function') {
                    res.then(resolve, reject);
                } else {
                    resolve(res);
                }
            } catch (err) {
                reject(err);
            }
        });
    }

    it('KimiCore.prototype.pauseGoal should exist and be a function', function() {
        let KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        if (!KimiCore) this.skip();
        assert.strictEqual(typeof KimiCore.prototype.pauseGoal, 'function', 'pauseGoal should be a function on the prototype');
    });

    })