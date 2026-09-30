let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0002.KimiCore with an enterSwarm method', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 should be present on module');
        assert.ok(testpilot_subject.file_0002.KimiCore, 'KimiCore should be present on file_0002');
        let proto = testpilot_subject.file_0002.KimiCore.prototype;
        assert.ok(proto, 'KimiCore.prototype should exist');
        assert.strictEqual(typeof proto.enterSwarm, 'function', 'enterSwarm should be a function on the prototype');
    });

    })