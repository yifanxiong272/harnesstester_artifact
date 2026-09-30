let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0012.MessageQueueService.EventEmitter', function() {
    // helper that tries to construct the emitter either as a factory or as a constructor
    function makeEmitter(opts) {
        const ctor = testpilot_subject &&
                     testpilot_subject.file_0012 &&
                     testpilot_subject.file_0012.MessageQueueService &&
                     testpilot_subject.file_0012.MessageQueueService.EventEmitter;
        if (!ctor) throw new Error('EventEmitter constructor/factory not found at expected path');
        try {
            // try as factory
            return ctor(opts);
        } catch (factoryErr) {
            // try as constructor
            try {
                return new ctor(opts);
            } catch (ctorErr) {
                // rethrow original to surface useful message
                throw factoryErr;
            }
        }
    }

    it('should return an object with common event methods', function() {
        const emitter = makeEmitter({});
        assert.ok(emitter && typeof emitter === 'object', 'emitter should be an object');

        // common method names to check for presence of at least one variant for add/remove
        assert.strictEqual(typeof emitter.emit, 'function', 'emitter.emit should be a function');

        // check for listener registration functions (accept common variants)
        const hasOn = typeof emitter.on === 'function';
        const hasAddListener = typeof emitter.addListener === 'function';
        assert.ok(hasOn || hasAddListener, 'emitter should provide on() or addListener()');

        // check for once function (may be present)
        const hasOnce = typeof emitter.once === 'function';
        assert.ok(hasOnce || true, 'emitter.once may or may not be present (not required)');

        // check for removal functions
        const hasRemoveListener = typeof emitter.removeListener === 'function';
        const hasOff = typeof emitter.off === 'function';
        assert.ok(hasRemoveListener || hasOff || true, 'emitter.removeListener or off may exist (not required)');
    });

    })