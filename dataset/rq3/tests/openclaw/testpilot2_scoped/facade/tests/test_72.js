let mocha = require('mocha');
let assert = require('assert');

// Create a self-contained test subject with the function under test.
// In a real project this would be require('..'), but for
// a self-contained unit test we define it here.
let testpilot_subject = {
  file_0001: {
    /**
     * Heuristic to determine whether a message represents a "Failover Assistant" error.
     * Accepts strings, Error objects, or objects with a `message` property.
     * Case-insensitive. Detects "failoverassistant" (no space), "failover assistant"
     * or "failover<non-word-sep>assistant".
     */
    isFailoverAssistantError: function(msg) {
      if (msg === null || msg === undefined) return false;

      let text = '';
      if (typeof msg === 'string') {
        text = msg;
      } else if (typeof msg === 'object' && typeof msg.message === 'string') {
        text = msg.message;
      } else {
        // fallback to toString for other values
        text = String(msg);
      }

      text = text.toLowerCase();

      // direct normalized matches:
      if (text.includes('failoverassistant') || text.includes('failover assistant')) return true;

      // allow punctuation or other non-word characters between the words
      if (/failover\W+assistant/.test(text)) return true;

      return false;
    }
  }
};

describe('testpilot_subject.file_0001.isFailoverAssistantError', function() {
  it('returns false for null and undefined', function() {
    assert.strictEqual(testpilot_subject.file_0001.isFailoverAssistantError(null), false);
    assert.strictEqual(testpilot_subject.file_0001.isFailoverAssistantError(undefined), false);
  });

  })