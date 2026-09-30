let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Slightly increase timeout in case implementation uses small async delays
    this.timeout(5000);

    // helper to safely call steer and capture sync throws / promise rejections / resolutions
    function invokeSteerSafely(fn, thisArg, arg) {
        try {
            const result = fn.call(thisArg, arg);
            if (result && typeof result.then === 'function') {
                // returned a promise-like
                return result.then(
                    value => ({ type: 'resolved', value }),
                    err => ({ type: 'rejected', error: err })
                );
            }
            // synchronous return
            return Promise.resolve({ type: 'resolved', value: result });
        } catch (err) {
            return Promise.resolve({ type: 'threw', error: err });
        }
    }

    it('KimiCore.prototype.steer exists and is a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject should be present');
        const file0002 = testpilot_subject.file_0002;
        assert.ok(file0002, 'file_0002 should exist on testpilot_subject');
        const KimiCore = file0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore should exist');
        assert.strictEqual(
            typeof KimiCore.prototype.steer,
            'function',
            'KimiCore.prototype.steer should be a function'
        );
    });

    })