let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0009.applyShellPath', function() {
        it('returns immediately and does not modify env when shellPath is null/undefined', function(done) {
            let env = { PATH: 'original' };
            // Make a shallow copy to compare later
            let before = Object.assign({}, env);

            // call with undefined
            testpilot_subject.file_0009.applyShellPath(env, undefined);
            assert.deepStrictEqual(env, before, 'env should be unchanged when shellPath is undefined');

            // call with null
            testpilot_subject.file_0009.applyShellPath(env, null);
            assert.deepStrictEqual(env, before, 'env should be unchanged when shellPath is null');

            done();
        });

            })
})