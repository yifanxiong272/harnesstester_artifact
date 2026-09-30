let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.sanitizeUserFacingText', function() {
        it('returns a string and is idempotent (sanitizing twice is same as once)', function() {
            const input = "Hello <b>World</b>\n  ";
            const out1 = testpilot_subject.file_0001.sanitizeUserFacingText(input, {});
            assert.strictEqual(typeof out1, 'string', 'output should be a string');
            const out2 = testpilot_subject.file_0001.sanitizeUserFacingText(out1, {});
            assert.strictEqual(out2, out1, 'sanitizing an already sanitized string should be a no-op (idempotent)');
        });

            })
})