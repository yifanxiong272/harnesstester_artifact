let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('OpenAICompatibleHandler constructor exists', function() {
        let Handler = testpilot_subject &&
                      testpilot_subject.file_0008 &&
                      testpilot_subject.file_0008.OpenAICompatibleHandler;
        assert.ok(typeof Handler === 'function', 'OpenAICompatibleHandler should be a constructor function');
    });

    })