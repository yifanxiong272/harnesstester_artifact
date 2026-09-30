let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  const ToolCallProto = testpilot_subject.file_0003.ToolCallComponent.prototype;
  let originalDateNow;

  beforeEach(function() {
    originalDateNow = Date.now;
  });

  afterEach(function() {
    Date.now = originalDateNow;
  });

  it('sets subagentEndedAtMs when name is "Agent" and started is set and ended is undefined', function() {
    // freeze Date.now to a known value
    Date.now = () => 1600000000000;
    const obj = {
      toolCall: { name: "Agent" },
      subagentStartedAtMs: 1599999999000,
      subagentEndedAtMs: undefined
    };

    ToolCallProto.finalizeSubagentElapsedIfNeeded.call(obj);

    assert.strictEqual(obj.subagentEndedAtMs, 1600000000000);
  });

  })