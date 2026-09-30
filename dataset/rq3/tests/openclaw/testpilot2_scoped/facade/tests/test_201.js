let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0008.applyShellPath', function() {
        it('does nothing when shellPath is falsy', function() {
            const env = { PATH: '/usr/bin' };
            // call with undefined
            testpilot_subject.file_0008.applyShellPath(env, undefined);
            assert.strictEqual(env.PATH, '/usr/bin');

            // call with empty string
            testpilot_subject.file_0008.applyShellPath(env, '');
            assert.strictEqual(env.PATH, '/usr/bin');

            // call with null
            testpilot_subject.file_0008.applyShellPath(env, null);
            assert.strictEqual(env.PATH, '/usr/bin');
        });

            })
})