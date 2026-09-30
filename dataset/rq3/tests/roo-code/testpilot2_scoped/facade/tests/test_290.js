let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.prototype.emit', function() {
    const Emitter = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('multi', function() {
        // create an emitter instance in a robust way (handle constructor or plain object)
        let emitter;
        if (typeof Emitter === 'function') {
            try {
                emitter = new Emitter();
            } catch (e) {
                // fallback if it isn't constructible
                emitter = Object.create(Emitter.prototype || Emitter);
            }
        } else if (Emitter && typeof Emitter === 'object') {
            emitter = Emitter;
        } else {
            emitter = {};
        }

        assert.ok(emitter, 'emitter should be created');

        // Ensure emit exists and is callable. The exact signature is unknown, so just check it doesn't throw.
        assert.strictEqual(typeof emitter.emit, 'function', 'emit should be a function');
        assert.doesNotThrow(() => emitter.em)    })
})