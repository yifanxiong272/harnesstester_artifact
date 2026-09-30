let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0011.stripRedundantSubsystemPrefixForConsole;

    it('returns a string for typical inputs', function() {
        // pass strings for the displaySubsystem argument (toLowerCase is called on it)
        const out1 = fn('SubsystemX: Doing work', 'SubsystemX');
        const out2 = fn('SubsystemY: SubsystemY: More work', 'SubsystemY');
        assert.strictEqual(typeof out1, 'string');
        assert.strictEqual(typeof out2, 'string');
    });

    })