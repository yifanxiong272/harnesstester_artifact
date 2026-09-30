let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0012.MessageQueueService.on should register a listener via emitter.on or emitter.addListener', function() {
        // Prepare a fake emitter that records calls to on/addListener
        const calls = [];
        const emitter = {
            on: function(eventName, cb) {
                calls.push({ method: 'on', eventName, cb });
            },
            addListener: function(eventName, cb) {
                calls.push({ method: 'addListener', eventName, cb });
            }
        };

        // Call the function under test
        const svc = testpilot_subject.file_0012 && testpilot_subject.file_0012.MessageQueueService;
        assert.ok(svc, 'MessageQueueService must be present on testpilot_subject.file_0012');

        // Use no options (should default to empty object)
        svc.on(emitter, 'myEvent');

        // Expect that either on or addListener was used to register the handler
        assert.ok(calls.length >= 1, 'Expected emitter.on or emitter.addListener to be called');
        const first = calls[0];
        assert.ok(
            first.method === 'on' || first.method === 'addListener',
            'Expected method to be "on" or "addListener"'
        );
        assert.strictEqual(first.eventName, 'myEvent', 'Event name passed to emitter must match');

        // The registered callback should be a function
        assert.strictEqual(typeof first.cb, 'function', 'Registered callback should be a function');
    });

    })