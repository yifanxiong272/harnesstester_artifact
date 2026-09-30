let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject &&
               testpilot_subject.file_0001 &&
               testpilot_subject.file_0001.formatRawAssistantErrorForUi;

    it('formatRawAssistantErrorForUi should exist and be a function', function() {
        assert.ok(fn, 'formatRawAssistantErrorForUi is not present on testpilot_subject.file_0001');
        assert.strictEqual(typeof fn, 'function');
    });

    })