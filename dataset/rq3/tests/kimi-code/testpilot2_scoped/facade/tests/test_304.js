let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;

    it('KimiCore exists and getBackground is a function on the prototype', function() {
        assert.ok(KimiCore, 'KimiCore should be exported');
        assert.ok(KimiCore.prototype, 'KimiCore.prototype should exist');
        assert.equal(typeof KimiCore.prototype.getBackground, 'function', 'getBackground should be a function on the prototype');
    });

    // helper to uniformly handle sync or Promise results from the method
    function asPromise(resultOrPromise) {
        if (resultOrPromise && typeof resultOrPromise.then === 'function') return resultOrPromise;
        return Promise.resolve(resultOrPromise);
    }

    })