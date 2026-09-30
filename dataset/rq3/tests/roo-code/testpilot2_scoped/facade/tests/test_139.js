let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0012.MessageQueueService.getMaxListeners', function() {
  const svc = testpilot_subject.file_0012.MessageQueueService;
  const getMaxListeners = svc.getMaxListeners;

  it('returns numeric value when object has numeric kMaxEventTargetListeners symbol property', function() {
    // The implementation checks for emitterOrTarget?.[kMaxEventTargetListeners] === 'number'
    // Try to get the symbol exported by the module; if it's not exported this test is skipped.
    const sym = svc.kMaxEventTargetListeners;
    if (typeof sym !== 'symbol') {
      // If the module does not expose the symbol, skip this assertion by simply returning.
      this.skip();
      return;
    }

    const obj = {};
    obj[sym] = 12345;
    const res = getMaxListeners(obj);
    assert.strictEqual(res, 12345);
  });

  })