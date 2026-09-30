let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.setMaxListeners', function() {
  const svc = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

  it('calls setMaxListeners on a single target object', function() {
    let calledWith = null;
    const target = {
      setMaxListeners(n) { calledWith = n; }
    };

    svc.setMaxListeners(5, target);

    assert.strictEqual(calledWith, 5, 'target.setMaxListeners should be called with the provided value');
  });

  })