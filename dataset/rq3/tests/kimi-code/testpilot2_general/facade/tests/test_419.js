let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  // Keep original clearTimeout so tests don't permanently modify global behavior
  let originalClearTimeout;

  beforeEach(function() {
    originalClearTimeout = global.clearTimeout;
  });

  afterEach(function() {
    // restore original clearTimeout
    global.clearTimeout = originalClearTimeout;
  });

  it('clears an existing pongTimer and sets pongTimer to undefined', function() {
    let called = 0;
    let receivedArg;
    // stub clearTimeout to observe calls
    global.clearTimeout = function(arg) {
      called += 1;
      receivedArg = arg;
    };

    const fakeThis = { pongTimer: 12345 };
    testpilot_subject.file_0006.WsConnection.prototype.onPong.call(fakeThis);

    assert.strictEqual(called, 1, 'clearTimeout should have been called once');
    assert.strictEqual(receivedArg, 12345, 'clearTimeout should be called with the pongTimer value');
    assert.strictEqual(fakeThis.pongTimer, undefined, 'pongTimer should be set to undefined after onPong');
  });

  })