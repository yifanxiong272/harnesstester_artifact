let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('returns listeners for a Node-style EventEmitter (addListener/removeListener or listeners())', function(done) {
        // Create a simple Node-style EventEmitter mock
        function makeNodeLikeEmitter() {
            const events = Object.create(null);
            return {
                addListener: function(type, listener) {
                    if (!events[type]) events[type] = [];
                    events[type].push(listener);
                },
                removeListener: function(type, listener) {
                    if (!events[type]) return;
                    const idx = events[type].indexOf(listener);
                    if (idx !== -1) events[type].splice(idx, 1);
                },
                // common Node API: listeners(type) -> array
                listeners: function(type) {
                    return events[type] ? events[type].slice() : [];
                },
                // expose for potential internals inspection
                _eventsForTest: events
            };
        }

        const emitter = makeNodeLikeEmitter();

        function a() {}
        function b() {}

        emitter.addListener('data', a);
        emitter.addListener('data', b);

        const res = testpilot_subject.file_0012.MessageQueueService.getEventListeners(emitter, 'data');

        assert.ok(Array.isArray(res), 'result should be an array');
        // At least both listeners should be present
        assert.ok(res.indexOf(a) !== -1, 'should contain listener a');
        assert.ok(res.indexOf(b) !== -1, 'should contain listener b');

        done();
    });

    })