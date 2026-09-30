let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const proto = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.prototype;
    const eventNamesFn = proto.eventNames;

    function arraysHaveSameMembers(a, b) {
        // Compare as sets (works for strings and symbols)
        if (a.length !== b.length) return false;
        const setB = new Set(b);
        for (const item of a) {
            if (!setB.has(item)) return false;
        }
        return true;
    }

    it('returns [] when _eventsCount is 0 even if _events has keys', function() {
        const ctx = Object.create(proto);
        // Put some keys in _events but leave _eventsCount at 0
        const sym = Symbol('ev');
        ctx._events = { someEvent: 1 };
        ctx._events[sym] = 2;
        ctx._eventsCount = 0;

        const result = eventNamesFn.call(ctx);
        assert(Array.isArray(result), 'result should be an array');
        assert.deepStrictEqual(result, [], 'should return empty array when _eventsCount is 0');
    });

    })