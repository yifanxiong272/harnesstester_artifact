let mocha = require('mocha');
let assert = require('assert');
let { EventEmitter } = require('events');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    this.timeout(5000);

    // helper to accept a few reasonable possible return shapes:
    // - a single value (e.g. 'hello')
    // - an array of args (e.g. ['hello'] or [1,2])
    // - an event-like object (e.g. { type: 'evt', detail: 'payload' })
    function assertResolvedValueMatches(actual, expected) {
        // If actual is an array, try to match by contents.
        if (Array.isArray(actual)) {
            // If expected is an array, do deep equality.
            if (Array.isArray(expected)) {
                return assert.deepStrictEqual(actual, expected);
            }
            // otherwise expect single-argument wrapper
            if (actual.length === 1 && (actual[0] === expected || (actual[0] && actual[0].detail === expected.detail))) {
                return;
            }
            // fallback deep equality
            return assert.deepStrictEqual(actual, [expected]);
        }

        // If both are plain objects, compare detail/type where available, otherwise deepEqual.
        if (actual && typeof actual === 'object' && expected && typeof expected === 'object') {
            if ('detail' in expected && actual.detail === expected.detail) return;
            if ('type' in expected && actual.type === expected.type) return;
            return assert.deepStrictEqual(actual, expected);
        }

        // If actual is a primitive, allow matching expected or expected.detail
        if (actual === expected) return;
        if (expected && typeof expected === 'object' && actual === expected.detail) return;

        // final fallback - fail with info
        assert.fail({actual, expected, message: 'resolved value did not match expected (see actual/expected)'});
    }

    it('resolves on first EventEmitter emission with single argument', async function() {
        const emitter = new EventEmitter();
        const promise = testpilot_subject.file_0012.MessageQueueService.once(emitter, 'evt');
        // emit the event with one argument
        emitter.em    })
})