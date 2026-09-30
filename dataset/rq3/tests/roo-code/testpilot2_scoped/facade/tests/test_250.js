let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('listeners() returns a shallow copy (mutating returned array does not change emitter state)', function(done) {
        const EER = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
        // Provide a name so AsyncResource/options.name is a string
        const ee = new EER('EventEmitterAsyncResource');

        function a() {}
        function b() {}

        ee.on('copyEvent', a);
        ee.on('copyEvent', b);

        const list = ee.listeners('copyEvent');
        // mutate returned array
        list.pop();
        // original emitter should still have both listeners
        const listAfter = ee.listeners('copyEvent');
        assert.strictEqual(listAfter.length, 2, 'emitter listeners should be unaffected by mutations to returned array');
        done();
    });

    })