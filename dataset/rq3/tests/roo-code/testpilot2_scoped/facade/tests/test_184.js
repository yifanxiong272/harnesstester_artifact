let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EventEmitterAsyncResource = testpilot_subject.file_0012
        .MessageQueueService
        .EventEmitter
        .EventEmitterAsyncResource;

    it('prependListener should return the emitter to allow chaining', function() {
        // Provide a name string to satisfy AsyncResource/constructor requirements
        const emitter = new EventEmitterAsyncResource('EventEmitterAsyncResource');
        function l() {}
        const ret = emitter.prependListener('x', l);
        assert.strictEqual(ret, emitter);
    });

    })