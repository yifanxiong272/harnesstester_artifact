let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('prototype listeners can be invoked with call/apply', function() {
        let EER = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
        // Provide a name to the AsyncResource-derived class to avoid the "options.name" error
        let ee = new EER('test');

        function x() {}
        let add = typeof ee.on === 'function' ? ee.on : ee.addListener;
        add.call(ee, 'evt', x);

        // Use prototype method directly via call to ensure it delegates properly
        let protoListeners = EER.prototype.listeners.call(ee, 'evt');
        assert.ok(Array.isArray(protoListeners));
        assert.strictEqual(protoListeners.length, 1);
        assert.strictEqual(protoListeners[0], x);
    });
});