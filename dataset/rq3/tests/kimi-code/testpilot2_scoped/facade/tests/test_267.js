let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case implementations return promises that take a moment
    this.timeout(5000);

    // Helper to call unregisterTool and normalize both sync and async returns into a Promise
    function invokeUnregister(core, args) {
        return new Promise((resolve, reject) => {
            try {
                let ret = core.unregisterTool(args);
                // If it returned a promise, wait for it
                if (ret && typeof ret.then === 'function') {
                    ret.then(resolve).catch(reject);
                } else {
                    resolve(ret);
                }
            } catch (err) {
                reject(err);
            }
        });
    }

    it('KimiCore.prototype.unregisterTool should exist and be a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace expected');
        assert.ok(testpilot_subject.file_0002.KimiCore, 'KimiCore constructor expected');
        let proto = testpilot_subject.file_0002.KimiCore.prototype;
        assert.ok(proto, 'KimiCore prototype expected');
        assert.strictEqual(typeof proto.unregisterTool, 'function', 'unregisterTool should be a function');
    });

    })