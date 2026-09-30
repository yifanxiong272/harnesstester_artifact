let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const Service = testpilot_subject &&
                    testpilot_subject.file_0012 &&
                    testpilot_subject.file_0012.MessageQueueService;
    const EventEmitter = Service && Service.EventEmitter;

    it('EventEmitter should be available and be a function', function() {
        assert.ok(Service, 'MessageQueueService should exist');
        assert.ok(EventEmitter, 'EventEmitter should exist');
        assert.strictEqual(typeof EventEmitter, 'function', 'EventEmitter should be a function');
    });

    describe('EventEmitter.init invocation behavior', function() {
        let originalInit;

        beforeEach(function() {
            // Save original init so we can restore it after each test
            originalInit = EventEmitter.init;
        });

        afterEach(function() {
            // Restore original init to avoid side effects between tests
            if (typeof originalInit === 'undefined') {
                delete EventEmitter.init;
            } else {
                EventEmitter.init = originalInit;
            }
        });

            })
})