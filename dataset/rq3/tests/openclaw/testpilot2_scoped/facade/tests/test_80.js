let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const sutContainer = testpilot_subject.file_0001 || testpilot_subject;
    const isFailoverErrorMessage = sutContainer.isFailoverErrorMessage;

    it('should export isFailoverErrorMessage as a function', function() {
        assert.strictEqual(typeof isFailoverErrorMessage, 'function', 'isFailoverErrorMessage should be a function');
    });

    })