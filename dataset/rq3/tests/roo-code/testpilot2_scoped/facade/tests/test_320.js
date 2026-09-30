let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0012.MessageQueueService.prototype.findMessage', function() {
        const Proto = testpilot_subject.file_0012.MessageQueueService.prototype;

        it('returns index -1 and undefined when there are no messages', function() {
            // create an object that uses the prototype method without calling constructor
            const svc = Object.create(Proto);
            svc._messages = [];

            const result = svc.findMessage('anything');
            assert.strictEqual(result.index, -1, 'expected index -1 when no messages');
            assert.strictEqual(result.message, undefined, 'expected message to be undefined when not found');
            // ensure internal array unchanged
            assert.deepStrictEqual(svc._messages, [], 'messages array should remain unchanged');
        });

            })
})