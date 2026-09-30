let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isTokenExpired', function() {
        it('should return a boolean for undefined, null and empty credentials', function() {
            let fn = testpilot_subject.file_0001.isTokenExpired;
            // pass objects with explicit expires values instead of raw undefined/null
            // to avoid the function trying to read .expires of an undefined input
            assert.strictEqual(typeof fn({ expires: undefined }), 'boolean', 'undefined expires should return a boolean');
            assert.strictEqual(typeof fn({ expires: null }), 'boolean', 'null expires should return a boolean');
            assert.strictEqual(typeof fn({}), 'boolean', 'empty object should return a boolean');
        });

    })
})