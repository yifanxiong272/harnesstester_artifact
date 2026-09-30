let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
let EventEmitter = require('events').EventEmitter;

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0012.MessageQueueService.getMaxListeners with Node EventEmitter', function() {
        let svc = testpilot_subject.file_0012.MessageQueueService;
        let emitter = new EventEmitter();
        // set a distinct value and ensure the service returns that value
        emitter.setMaxListeners(42);
        let result = svc.getMaxListeners(emitter);
        assert.strictEqual(result, 42, 'should return the value set via EventEmitter.setMaxListeners');
    });

    })