let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('listeners returns the registered listeners in order', function() {
        let EER = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
        // Provide a name option so AsyncResource-based constructors that expect options.name don't fail.
        let ee = new EER({ name: 'EventEmitterAsyncResource' });

        // functions to register
        function a() {}
        function b() {}

        // register using whichever API is present (.on preferred, fallback to .addListener)
        let add = typeof ee.on === 'function' ? ee.on : ee.addListener;
        assert.strictEqual(typeof add, 'function', 'Expected an add listener function (on/addListener)');

        add.call(ee, 'my-event', a);
        add.call(ee, 'my-event', b);

        let listeners = ee.listeners('my-event');
        assert.ok(Array.isArray(listeners), 'listeners should return an array');
        assert.strictEqual(listeners.length, 2, 'Expected two listeners');
        assert.strictEqual(listeners[0], a, 'first listener should be the first added');
        assert.strictEqual(listeners[1], b, 'second listener should be the second added');

        // ensure the returned array is a shallow copy: mutating it shouldn't affect the emitter
        listeners.pop();
        let listenersAfter = ee.listeners('my-event');
        assert.strictEqual(listenersAfter.length, 2, 'Modifying returned array should not remove actual listeners');
    });

    })