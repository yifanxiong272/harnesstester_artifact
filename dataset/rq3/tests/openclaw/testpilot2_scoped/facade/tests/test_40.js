let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isAuthErrorMessage', function() {
        const isAuth = testpilot_subject.file_0001.isAuthErrorMessage;

        it('should return false for null, undefined and empty/whitespace strings', function() {
            assert.strictEqual(isAuth(null), false, 'null should not be considered an auth error');
            assert.strictEqual(isAuth(undefined), false, 'undefined should not be considered an auth error');
            assert.strictEqual(isAuth(''), false, 'empty string should not be considered an auth error');
            assert.strictEqual(isAuth('   '), false, 'whitespace-only string should not be considered an auth error');
        });

            })
})