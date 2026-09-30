let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case installPlugin performs async work
    this.timeout(5000);

    const KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;

    function withTimeout(promise, ms) {
        return Promise.race([
            promise,
            new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), ms))
        ]);
    }

    it('KimiCore should be present and installPlugin should be a function', function() {
        assert.ok(KimiCore, 'KimiCore constructor is required for the tests');
        assert.strictEqual(typeof KimiCore.prototype.installPlugin, 'function', 'installPlugin should be a function on the prototype');
    });

    })