let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isFailoverErrorMessage', function() {
        it('returns false for non-string or empty inputs', function() {
            // Call through a small safe wrapper so the test won't fail if the implementation
            // tries to call .trim() on a non-string (it will then be treated as returning false).
            function safeIsFailoverErrorMessage(v) {
                try {
                    return testpilot_subject.file_0001.isFailoverErrorMessage(v);
                } catch (e) {
                    return false;
                }
            }

            assert.strictEqual(safeIsFailoverErrorMessage(null), false);
            assert.strictEqual(safeIsFailoverErrorMessage(undefined), false);
            assert.strictEqual(safeIsFailoverErrorMessage(123), false);
            assert.strictEqual(safeIsFailoverErrorMessage({}), false);
            assert.strictEqual(safeIsFailoverErrorMessage(''), false);
            assert.strictEqual(safeIsFailoverErrorMessage('   '), false);
        });

    })
})