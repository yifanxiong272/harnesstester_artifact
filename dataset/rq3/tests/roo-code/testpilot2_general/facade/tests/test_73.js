let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('testpilot_subject.file_0001.generateState should exist and be a function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject must be present');
        assert.ok(testpilot_subject.file_0001, 'module must export file_0001');
        assert.strictEqual(typeof testpilot_subject.file_0001.generateState, 'function',
            'generateState should be a function');
    });

    })