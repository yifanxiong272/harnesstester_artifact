let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0002.FsSearchService.None.dispose', function() {
  // helper to uniformly handle sync / promise results from dispose()
  function handleResult(res, done) {
    if (res && typeof res.then === 'function') {
      res.then(() => done()).catch(done);
    } else {
      // synchronous result
      done();
    }
  }

  it('dispose should exist and be a function', function() {
    const dispose = testpilot_subject?.file_0002?.FsSearchService?.None?.dispose;
    assert.ok(dispose !== undefined, 'dispose should be defined');
    assert.strictEqual(typeof dispose, 'function', 'dispose should be a function');
  });

  })