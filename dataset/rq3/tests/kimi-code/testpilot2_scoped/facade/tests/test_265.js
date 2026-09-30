let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call registerTool and normalize sync throw into a rejected Promise
    function callRegister(core, arg) {
        try {
            return Promise.resolve(core.registerTool(arg));
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('test testpilot_subject.file_0002.KimiCore.prototype.registerTool - exists and is a function', function() {
        let KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore constructor should exist');
        assert.strictEqual(typeof KimiCore.prototype.registerTool, 'function', 'registerTool should be a function on the prototype');
    });

    })