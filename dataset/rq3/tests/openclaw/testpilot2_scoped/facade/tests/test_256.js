let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const normalize = testpilot_subject.file_0008.normalizeExecHost;

    it('returns normalized lowercase keyword for valid inputs', function() {
        assert.strictEqual(normalize('sandbox'), 'sandbox');
        assert.strictEqual(normalize('  GATEWAY  '), 'gateway');
        assert.strictEqual(normalize('NoDe'), 'node');
        // also ensure trimming is applied
        assert.strictEqual(normalize('  sandbox\t\n'), 'sandbox');
    });

    })