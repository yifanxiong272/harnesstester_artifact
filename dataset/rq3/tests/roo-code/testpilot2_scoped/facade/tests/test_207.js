let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EPath = testpilot_subject
        && testpilot_subject.file_0012
        && testpilot_subject.file_0012.MessageQueueService
        && testpilot_subject.file_0012.MessageQueueService.EventEmitter
        && testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('exports EventEmitterAsyncResource constructor', function() {
        assert.ok(EPath, 'EventEmitterAsyncResource class is available at the expected path');
        // Should be a constructor / function
        assert.ok(
            typeof EPath === 'function' || typeof EPath === 'object',
            'EventEmitterAsyncResource should be a constructor or function-like'
        );
    });

    })