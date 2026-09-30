let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0016.resolveAcpClientSpawnInvocation', function() {
    it('is exported as a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0016, 'file_0016 namespace should exist');
        assert.strictEqual(typeof testpilot_subject.file_0016.resolveAcpClientSpawnInvocation, 'function', 'resolveAcpClientSpawnInvocation should be a function');
    });

    })