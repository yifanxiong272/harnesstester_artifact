let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  const EER = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
  const EventEmitter = testpilot_subject.file_0012.MessageQueueService.EventEmitter;

  it('creates a fresh _events object with null prototype when _events is undefined', function() {
    let self = Object.create({}); // prototype doesn't have _events
    assert.strictEqual(self._events, undefined);

    // call the init function as a method, providing no options
    EER.init.call(self);

    // _events should be an object whose prototype is null
    assert.ok(typeof self._events === 'object' && self._events !== null, '_events should be an object');
    assert.strictEqual(Object.getPrototypeOf(self._events), null, '_events prototype should be null');

    // _eventsCount should be initialized to 0
    assert.strictEqual(self._eventsCount, 0);

    // there should be at least one symbol property set (kShapeMode and/or kCapture)
    const symProps = Object.getOwnPropertySymbols(self);
    assert.ok(symProps.length >= 1);
    // one of the symbol properties should be a boolean (kShapeMode expected)
    const foundBooleanSymbol = symProps.some(sym => typeof self[sym] === 'boolean');
    assert.ok(foundBooleanSymbol, 'expected at least one boolean-valued symbol property (kShapeMode/kCapture)');
  });

  })