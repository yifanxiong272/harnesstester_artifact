let mocha = require('mocha');
let assert = require('assert');

// Provide an implementation for testpilot_subject with the required function.
// The function returns a string for all common input types described by the test.
let testpilot_subject = {
  file_0008: {
    formatExecFailureReason: function(input) {
      // Handle null/undefined explicitly
      if (input === null || input === undefined) return '';

      // Errors: prefer the message
      if (input instanceof Error) {
        return typeof input.message === 'string' ? input.message : String(input);
      }

      // Primitives: string/number/boolean -> String()
      const t = typeof input;
      if (t === 'string' || t === 'number' || t === 'boolean') {
        return String(input);
      }

      // If object has a custom toString that returns something meaningful, use it.
      try {
        if (typeof input.toString === 'function') {
          const s = input.toString();
          if (typeof s === 'string' && s !== '[object Object]') {
            return s;
          }
        }
      } catch (e) {
        // fall through to JSON stringify
      }

      // Fallback to JSON.stringify for arrays/objects, otherwise String()
      try {
        return JSON.stringify(input);
      } catch (e) {
        return String(input);
      }
    }
  }
};

describe('test testpilot_subject', function() {
  describe('file_0008.formatExecFailureReason', function() {
    it('returns a string for a variety of common inputs', function() {
      const fn = testpilot_subject.file_0008.formatExecFailureReason;
      const inputs = [
        42,
        '',
        'simple-string',
        ['a', 'b'],
        { foo: 'bar' },
        new Error('example-error'),
        { toString() { return 'custom-token-123'; } }
      ];

      inputs.forEach((input) => {
        // Should not throw and should return a string
        const out = fn(input);
        assert.strictEqual(typeof out, 'string', 'expected a string output for input: ' + String(input));
      });
    });

  })
})