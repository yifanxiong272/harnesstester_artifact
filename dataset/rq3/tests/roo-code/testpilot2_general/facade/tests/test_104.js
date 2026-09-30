let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  let OutputManagerProto = testpilot_subject.file_0002.OutputManager.prototype;
  let om, written;

  beforeEach(function() {
    // Create an object that has the prototype but does not run any constructor logic.
    om = Object.create(OutputManagerProto);
    written = [];
    // Provide a fake stderr with a write method that captures output.
    om.stderr = {
      write: function(s) { written.push(s); }
    };
    // Ensure disabled flag defaults to false for tests (explicitly set).
    om.disabled = false;
  });

  it('writes "label text\\n" when text is provided', function() {
    om.outputError('ERR', 'something');
    assert.strictEqual(written.length, 1, 'stderr.write should be called once');
    assert.strictEqual(written[0], 'ERR something\n');
  });

  })