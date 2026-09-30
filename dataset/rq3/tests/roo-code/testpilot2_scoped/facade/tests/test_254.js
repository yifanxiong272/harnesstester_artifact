let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EmitterClass = testpilot_subject &&
                         testpilot_subject.file_0012 &&
                         testpilot_subject.file_0012.MessageQueueService &&
                         testpilot_subject.file_0012.MessageQueueService.EventEmitter &&
                         testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('has the EventEmitterAsyncResource constructor available', function() {
        assert.ok(EmitterClass, 'EventEmitterAsyncResource constructor should exist on testpilot_subject.file_0012.MessageQueueService.EventEmitter');
        assert.equal(typeof EmitterClass, 'function', 'EventEmitterAsyncResource should be a constructor function');
        assert.ok(typeof EmitterClass.prototype.rawListeners === 'function', 'rawListeners should be a function on the prototype');
    });

    })