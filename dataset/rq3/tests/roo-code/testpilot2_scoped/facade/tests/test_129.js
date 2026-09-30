let mocha = require('mocha');
let assert = require('assert');
let { EventEmitter } = require('events');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  const once = testpilot_subject.file_0012.MessageQueueService.once;

  it('resolves with event arguments from a Node EventEmitter', async function() {
    const emitter = new EventEmitter();
    const p = once(emitter, 'myevent');
    // emit with multiple args
    emitter.em    })
})