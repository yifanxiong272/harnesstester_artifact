let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.prototype.rawListeners', function() {
    const proto = testpilot_subject &&
                  testpilot_subject.file_0012 &&
                  testpilot_subject.file_0012.MessageQueueService &&
                  testpilot_subject.file_0012.MessageQueueService.EventEmitter &&
                  testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource &&
                  testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.prototype;

    it('should expose the rawListeners function on the prototype', function() {
        assert.ok(proto, 'prototype object is not present on testpilot_subject');
        assert.strictEqual(typeof proto.rawListeners, 'function', 'rawListeners must be a function');
    });

    })