let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0009.normalizeExecSecurity - function exists and is callable', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.strictEqual(typeof testpilot_subject.file_0009.normalizeExecSecurity, 'function',
            'normalizeExecSecurity should be a function');
    });

    })