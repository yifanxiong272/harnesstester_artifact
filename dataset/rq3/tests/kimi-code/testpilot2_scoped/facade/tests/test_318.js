let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0002.KimiCore as a constructor function', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 should be exported');
        assert.strictEqual(typeof testpilot_subject.file_0002.KimiCore, 'function', 'KimiCore should be a function (constructor)');
    });

    })