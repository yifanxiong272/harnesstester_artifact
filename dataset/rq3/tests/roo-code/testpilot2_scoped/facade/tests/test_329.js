let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const MessageQueueService = testpilot_subject.file_0012.MessageQueueService;

    it('should dequeue the first message and emit stateChanged with the remaining messages', function(done) {
        const svc = new MessageQueueService();
        // set up an initial queue
        svc._messages = ['first', 'second', 'third'];

        // capture emitted events
        let seen = { count: 0, args: [] };
        svc.on('stateChanged', function(arg) {
            seen.count++;
            // copy the argument so later mutations don't affect our recorded value
            seen.args.push(Array.isArray(arg) ? arg.slice() : arg);
        });

        const returned = svc.dequeueMessage();

        // should return the first message
        assert.strictEqual(returned, 'first');

        // internal message queue should now start with 'second'
        assert.deepStrictEqual(svc._messages, ['second', 'third']);

        // stateChanged should have been emitted exactly once with the new queue
        assert.strictEqual(seen.count, 1);
        assert.deepStrictEqual(seen.args[0], ['second', 'third']);

        done();
    });

    })