let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.exchangeCodeForTokens', function() {
        it('is exported as a function', function() {
            assert.strictEqual(typeof testpilot_subject.file_0001.exchangeCodeForTokens, 'function',
                'exchangeCodeForTokens should be a function');
        });

            })
})