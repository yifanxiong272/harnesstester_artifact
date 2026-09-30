let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0002.KimiCore.prototype.closeSession', function() {
    const KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;

    it('should exist and be an async function', function() {
        assert.ok(KimiCore, 'KimiCore constructor must be present');
        const fn = KimiCore.prototype.closeSession;
        assert.ok(typeof fn === 'function', 'closeSession must be a function');
        // Async functions have constructor name "AsyncFunction"
        assert.strictEqual(fn.constructor.name, 'AsyncFunction', 'closeSession should be declared async');
    });

    })