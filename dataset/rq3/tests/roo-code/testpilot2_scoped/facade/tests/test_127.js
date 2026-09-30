let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0012.MessageQueueService.addAbortListener', function() {
  it('throws when signal is undefined', function() {
    assert.throws(
      () => {
        testpilot_subject.file_0012.MessageQueueService.addAbortListener(undefined, () => {});
      },
      (err) => err && err.code === 'ERR_INVALID_ARG_TYPE'
    );
  });

  })