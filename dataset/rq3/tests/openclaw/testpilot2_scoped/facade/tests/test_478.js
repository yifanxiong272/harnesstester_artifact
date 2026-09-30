let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0016.resolveAcpClientSpawnInvocation', function() {
        const fn = testpilot_subject && testpilot_subject.file_0016 && testpilot_subject.file_0016.resolveAcpClientSpawnInvocation;
        it('is exported as a function', function() {
            assert.ok(fn, 'function missing from export');
            assert.strictEqual(typeof fn, 'function');
        });

            })
})