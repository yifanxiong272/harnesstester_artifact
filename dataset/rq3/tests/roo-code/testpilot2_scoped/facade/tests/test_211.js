let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const proto = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.prototype;

    // Helper to create a lightweight "emitter" object that uses the real prototype method,
    // but where we can freely set internal fields (_events, _eventsCount, emit, etc.)
    function makeEmitter() {
        return Object.create(proto);
    }

    it('removeListener returns the same object when there are no events', function() {
        const em = makeEmitter();
        em._events = undefined;
        em._eventsCount = 0;

        function fn() {}
        const ret = proto.removeListener.call(em, 'nope', fn);
        assert.strictEqual(ret, em);
        // nothing should have changed
        assert.strictEqual(em._events, undefined);
        assert.strictEqual(em._eventsCount, 0);
    });

    })