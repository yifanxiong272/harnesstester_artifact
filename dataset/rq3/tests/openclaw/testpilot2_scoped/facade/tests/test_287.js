let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject &&
               testpilot_subject.file_0009 &&
               testpilot_subject.file_0009.isValidCloudCodeAssistToolId;

    it('exports isValidCloudCodeAssistToolId as a function', function() {
        assert.strictEqual(typeof fn, 'function', 'isValidCloudCodeAssistToolId should be a function');
    });

    })