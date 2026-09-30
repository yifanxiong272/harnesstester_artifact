let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const parse = testpilot_subject &&
                  testpilot_subject.file_0007 &&
                  testpilot_subject.file_0007.parseExtensionMessage;

    it('parseExtensionMessage should be a function', function() {
        assert.strictEqual(typeof parse, 'function', 'parseExtensionMessage is not a function');
    });

    })