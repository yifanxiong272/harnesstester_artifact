let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper: create an instance of MessageQueueService in a resilient way
    function createInstance() {
        const container = testpilot_subject && testpilot_subject.file_0012;
        assert.ok(container, 'testpilot_subject.file_0012 must exist');
        const Cls = container.MessageQueueService;
        assert.ok(typeof Cls === 'function', 'MessageQueueService constructor must exist');

        // Try to construct normally, otherwise fall back to Object.create of prototype
        try {
            return new Cls();
        } catch (e1) {
            try {
                return new Cls(undefined);
            } catch (e2) {
                // best-effort: create an object with the right prototype (constructor may require args)
                return Object.create(Cls.prototype);
            }
        }
    }

    // Helper: pick or create a likely internal queue property to manipulate for tests
    function pickQueueProp(instance) {
        const candidates = [
            'queue', 'messages', '_queue', '_messages',
            'messageQueue', 'message_queue', 'msgs', 'buffer', '_buffer'
        ];
        for (let p of candidates) {
            if (Object.prototype.hasOwnProperty.call(instance, p) || p in instance) {
                return p;
            }
        }
        // none found: create 'queue'
        instance.queue = instance.queue || [];
        return 'queue';
    }

    // Helper: normalize the possible sync/async return of dequeueMessage to a Promise
    function asPromise(val) {
        if (val && typeof val.then === 'function') {
            return val;
        }
        return Promise.resolve(val);
    }

    it('MessageQueueService should exist and expose dequeueMessage', function() {
        const svc = createInstance();
        assert.ok(svc, 'unable to create instance');
        assert.strictEqual(typeof svc.dequeueMessage, 'function', 'dequeueMessage must be a function');
    });

    })