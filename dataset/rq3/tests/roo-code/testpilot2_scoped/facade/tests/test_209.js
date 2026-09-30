let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  const EventEmitterAsyncResource = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

  it('throws when listener is not a function', function() {
    // provide a name so AsyncResource options.name is defined
    const emitter = new EventEmitterAsyncResource('EventEmitterAsyncResource');
    assert.throws(
      () => emitter.prependOnceListener('evt', null),
      {
        name: 'TypeError'
      },
      'prependOnceListener should throw when listener is not a function'
    );
  });

  })