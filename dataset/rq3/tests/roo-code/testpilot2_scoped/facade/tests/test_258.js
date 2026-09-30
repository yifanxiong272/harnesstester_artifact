let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EER = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('has a listenerCount function on the prototype', function() {
        assert.strictEqual(typeof EER.prototype.listenerCount, 'function');
    });

    })