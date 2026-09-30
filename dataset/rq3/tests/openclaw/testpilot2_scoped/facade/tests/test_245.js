let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0008.findPathKey', function() {
        it('returns "PATH" when env has exact PATH property', function() {
            const env = { PATH: '/usr/bin' };
            const res = testpilot_subject.file_0008.findPathKey(env);
            assert.strictEqual(res, 'PATH');
        });

            })
})