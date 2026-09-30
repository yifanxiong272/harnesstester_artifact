let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0016.runAcpClientInteractive', function() {
    it('should exist on testpilot_subject.file_0016', function() {
        assert.ok(testpilot_subject, 'testpilot_subject module is present');
        assert.ok(testpilot_subject.file_0016, 'file_0016 namespace is present on module');
        assert.ok(typeof testpilot_subject.file_0016.runAcpClientInteractive === 'function',
            'runAcpClientInteractive is a function');
    });

    })