let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // A little extra timeout in case the implementation does async work
    this.timeout(2000);

    it('test testpilot_subject.file_0002.KimiCore.prototype.listPlugins - exists and is async', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');

        let KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore class should exist at testpilot_subject.file_0002.KimiCore');

        let fn = KimiCore.prototype.listPlugins;
        assert.strictEqual(typeof fn, 'function', 'listPlugins should be a function');

        // Detect async function constructor
        const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
        assert.strictEqual(fn.constructor, AsyncFunction, 'listPlugins should be declared async');
    });

    })