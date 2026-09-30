let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the removeListener implementation from the prototype
    const proto = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.prototype;
    const removeListener = proto.removeListener;

    it('removes a sole listener stored as a function', function() {
        let fake = { _events: {} };
        function listener() {}
        fake._events['myEvent'] = listener;

        // Call the prototype method with our fake "this"
        removeListener.call(fake, 'myEvent', listener);

        // After removal there should be no listener for the event
        assert.strictEqual(fake._events['myEvent'], undefined);
    });

    })