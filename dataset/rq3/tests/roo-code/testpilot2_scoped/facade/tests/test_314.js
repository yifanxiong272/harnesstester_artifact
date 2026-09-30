let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  const EventEmitter = testpilot_subject.file_0012.MessageQueueService.EventEmitter;
  const emit = EventEmitter.prototype.emit;

  it('emit should return false for non-error when there are no listeners (_events undefined)', function() {
    const emitter = Object.create(EventEmitter.prototype);
    // Ensure no _events property
    delete emitter._events;
    const result = emit.call(emitter, 'someEvent', 1, 2, 3);
    assert.strictEqual(result, false);
  });

  })