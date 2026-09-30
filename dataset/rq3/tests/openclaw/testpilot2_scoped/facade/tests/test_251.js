let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    const normalize = testpilot_subject.file_0008.normalizeExecAsk;

    it('returns canonical values for recognized inputs (case-insensitive, trimmed)', function() {
        assert.strictEqual(normalize('OFF'), 'off');
        assert.strictEqual(normalize('  On-MiSs  '), 'on-miss');
        assert.strictEqual(normalize('always'), 'always');
        // also check already-canonical
        assert.strictEqual(normalize('on-miss'), 'on-miss');
    });

    })