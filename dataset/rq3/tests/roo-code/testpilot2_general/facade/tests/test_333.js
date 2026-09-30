let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0007.isValidExtensionMessage - is a function', function() {
        assert.strictEqual(typeof testpilot_subject.file_0007.isValidExtensionMessage, 'function');
    });

    })