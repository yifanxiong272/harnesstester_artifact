let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('listeners() returns registered listeners in the order they were added', function(done) {
        const EER = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.EventEmitterAsyncResource || testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
        // Provide a name string because the AsyncResource-derived constructor expects options.name to be a string
        const ee = new EER('test-event-emitter');

        function a() { return 'a'; }
        function b() { return 'b'; }

        ee.on('myEvent', a);
        ee.on('myEvent', b);

        const list = ee.listeners('myEvent');
        assert.strictEqual(list.length, 2, 'should have two listeners');
        assert.strictEqual(list[0], a, 'first listener should be the first added');
        assert.strictEqual(list[1], b, 'second listener should be the second added');
        done();
    });

})