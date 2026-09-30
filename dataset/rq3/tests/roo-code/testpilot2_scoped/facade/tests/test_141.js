let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  it('calls emitter.listenerCount when present', function() {
    const L = testpilot_subject.file_0012.MessageQueueService.listenerCount;
    let seenType = null;
    const emitter = {
      listenerCount(type) {
        seenType = type;
        return 42;
      }
    };

    const result = L(emitter, 'my-event');
    assert.strictEqual(seenType, 'my-event');
    assert.strictEqual(result, 42);
  });

  })