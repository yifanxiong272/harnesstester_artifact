let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0009.normalizeExecSecurity', function() {
        it('returns the same lowercase token for valid values', function() {
            const fn = testpilot_subject.file_0009.normalizeExecSecurity;
            assert.strictEqual(fn('deny'), 'deny');
            assert.strictEqual(fn('allowlist'), 'allowlist');
            assert.strictEqual(fn('full'), 'full');
        });

            })
})