let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should have transformMessagesForCondensing exported as a function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        assert.strictEqual(typeof testpilot_subject.file_0004.transformMessagesForCondensing, 'function',
            'transformMessagesForCondensing should be a function');
    });

    })