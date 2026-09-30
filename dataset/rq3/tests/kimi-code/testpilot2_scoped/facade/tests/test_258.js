let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // small helper to detect Promise-like
    function isPromise(obj) {
        return !!obj && (typeof obj.then === 'function');
    }

    // helper that resolves when promise settles (resolve or reject) within ms, otherwise rejects
    function settlesWithin(promise, ms) {
        return new Promise((resolve, reject) => {
            let timer = setTimeout(() => {
                reject(new Error('Promise did not settle within ' + ms + 'ms'));
            }, ms);
            promise.then(
                () => { clearTimeout(timer); resolve(); },
                () => { clearTimeout(timer); resolve(); } // treat rejection as "settled"
            );
        });
    }

    it('KimiCore and getSwarmMode exist and is a function', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should exist');
        const KimiCore = testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore should be exported');
        assert.strictEqual(typeof KimiCore.prototype.getSwarmMode, 'function',
            'KimiCore.prototype.getSwarmMode should be a function');
    });

    })