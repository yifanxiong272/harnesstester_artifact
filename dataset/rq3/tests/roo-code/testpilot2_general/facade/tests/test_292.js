let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0007.MessageProcessor - module shape', function(done) {
        // Ensure the path exists and is a function / constructor
        assert.ok(testpilot_subject, 'testpilot_subject should be defined');
        let MessageProcessor = testpilot_subject.file_0007 && testpilot_subject.file_0007.MessageProcessor;
        assert.ok(MessageProcessor, 'MessageProcessor export should exist');
        assert.equal(typeof MessageProcessor, 'function', 'MessageProcessor should be a function/constructor');
        done();
    });

    })