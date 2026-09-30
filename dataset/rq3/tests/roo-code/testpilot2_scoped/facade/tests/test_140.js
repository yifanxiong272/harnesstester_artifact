let mocha = require('mocha');
let assert = require('assert');
let EventEmitter = require('events').EventEmitter;
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0012.MessageQueueService.listenerCount', function() {

        it('counts listeners on a Node EventEmitter', function() {
            let emitter = new EventEmitter();

            // Initially no listeners for 'ping'
            assert.strictEqual(
                testpilot_subject.file_0012.MessageQueueService.listenerCount(emitter, 'ping'),
                0,
                'expected 0 listeners initially'
            );

            function l1() {}
            function l2() {}

            emitter.on('ping', l1);
            assert.strictEqual(
                testpilot_subject.file_0012.MessageQueueService.listenerCount(emitter, 'ping'),
                1,
                'expected 1 listener after adding one'
            );

            emitter.on('ping', l2);
            assert.strictEqual(
                testpilot_subject.file_0012.MessageQueueService.listenerCount(emitter, 'ping'),
                2,
                'expected 2 listeners after adding a second'
            );

            emitter.removeListener('ping', l1);
            assert.strictEqual(
                testpilot_subject.file_0012.MessageQueueService.listenerCount(emitter, 'ping'),
                1,
                'expected 1 listener after removing one'
            );

            emitter.removeAllListeners('ping');
            assert.strictEqual(
                testpilot_subject.file_0012.MessageQueueService.listenerCount(emitter, 'ping'),
                0,
                'expected 0 listeners after removeAllListeners'
            );
        });

            })
})