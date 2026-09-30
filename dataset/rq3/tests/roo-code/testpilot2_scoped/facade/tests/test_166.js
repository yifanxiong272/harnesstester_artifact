let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EEARes = testpilot_subject
        && testpilot_subject.file_0012
        && testpilot_subject.file_0012.MessageQueueService
        && testpilot_subject.file_0012.MessageQueueService.EventEmitter
        && testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('constructor and prototype should exist', function() {
        assert.ok(EEARes, 'EventEmitterAsyncResource constructor should exist');
        assert.ok(EEARes.prototype, 'prototype should exist');
        assert.strictEqual(typeof EEARes.prototype.getMaxListeners, 'function', 'getMaxListeners should be a function on the prototype');
    });

    })