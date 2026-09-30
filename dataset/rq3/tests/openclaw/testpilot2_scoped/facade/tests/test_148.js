let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  it('should export a value', function() {
    // Basic sanity check: the module should export something.
    assert.ok(testpilot_subject, 'testpilot_subject should be defined');
  });
});