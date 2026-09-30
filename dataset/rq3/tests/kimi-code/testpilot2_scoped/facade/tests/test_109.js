let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a safe "this" proxy so that archiveSession can call any property/method
    // without touching external resources. Any property access returns a thenable no-op,
    // and any function call returns a resolved Promise.
    function createSafeThis() {
        let prox = null;
        const noopFn = (...args) => Promise.resolve();
        prox = new Proxy(noopFn, {
            get(target, prop) {
                // Return the proxy itself for any property access so chained accesses work.
                return prox;
            },
            apply(target, thisArg, args) {
                // If the archiveSession calls a function on this, return a resolved promise.
                return Promise.resolve();
            },
            construct(target, args) {
                // If it's used as a constructor, return the proxy object.
                return prox;
            }
        });
        return prox;
    }

    it('KimiCore.prototype.archiveSession should exist and be a function', function() {
        const KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore class missing from module');
        assert.strictEqual(typeof KimiCore.prototype.archiveSession, 'function', 'archiveSession is not a function');
    });

    })