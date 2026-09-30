let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('module and function exist', function() {
        assert.ok(testpilot_subject, 'testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0011, 'testpilot_subject.file_0011 should be present');
        assert.strictEqual(typeof testpilot_subject.file_0011.runtimeForLogger, 'function', 'runtimeForLogger should be a function');
    });

    })