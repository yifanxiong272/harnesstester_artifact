let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EventEmitterAsyncResource = testpilot_subject.file_0012
        .MessageQueueService
        .EventEmitter
        .EventEmitterAsyncResource;

    it('prependListener should throw a TypeError when listener is not a function', function() {
        // Provide a name to the AsyncResource-based class to satisfy options.name requirement
        const emitter = new EventEmitterAsyncResource('test');
        // Common behavior for EventEmitter: non-function listener => TypeError
        assert.throws(() => {
            emitter.prependListener('evt', null);
        }, TypeError);
        assert.throws(() => {
            emitter.prependListener('evt', 123);
        }, TypeError);
        assert.throws(() => {
            emitter.prependListener('evt', {});
        }, TypeError);
    });

    })