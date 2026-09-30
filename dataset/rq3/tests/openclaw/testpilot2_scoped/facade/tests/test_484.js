let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0016.shouldStripProviderAuthEnvVarsForAcpServer', function() {
    const fn = testpilot_subject &&
               testpilot_subject.file_0016 &&
               testpilot_subject.file_0016.shouldStripProviderAuthEnvVarsForAcpServer;

    it('exists and is a function', function() {
        assert.strictEqual(typeof fn, 'function', 'expected function to be exported');
    });

    })