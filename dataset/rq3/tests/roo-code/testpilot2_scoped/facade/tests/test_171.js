let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const E = testpilot_subject &&
              testpilot_subject.file_0012 &&
              testpilot_subject.file_0012.MessageQueueService &&
              testpilot_subject.file_0012.MessageQueueService.EventEmitter &&
              testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('has EventEmitterAsyncResource constructor available', function() {
        assert.ok(E, 'EventEmitterAsyncResource constructor should exist on testpilot_subject');
        assert.strictEqual(typeof E, 'function', 'EventEmitterAsyncResource should be a constructor function');
    });

    })