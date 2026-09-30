let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EmitterClass = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
    const proto = EmitterClass && EmitterClass.prototype;

    it('EventEmitterAsyncResource.prototype.eventNames should exist and be a function', function() {
        assert.ok(proto, 'prototype is present');
        assert.strictEqual(typeof proto.eventNames, 'function', 'eventNames should be a function on the prototype');
    });

    })