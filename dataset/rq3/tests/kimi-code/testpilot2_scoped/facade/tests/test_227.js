let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.KimiCore.prototype.getModel - API surface', function() {
        // basic existence checks
        assert.ok(testpilot_subject, 'testpilot_subject should be defined');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should be defined');
        assert.ok(testpilot_subject.file_0002.KimiCore, 'KimiCore should be defined');
        assert.strictEqual(
            typeof testpilot_subject.file_0002.KimiCore.prototype.getModel,
            'function',
            'KimiCore.prototype.getModel should be a function'
        );
    });

    })