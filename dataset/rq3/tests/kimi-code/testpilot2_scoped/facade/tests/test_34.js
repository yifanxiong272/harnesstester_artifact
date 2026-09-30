let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0001.FsWatcherService.None.dispose', function() {
    let svc;

    before(function() {
      // Basic existence checks so tests fail fast with clear messages if shape is different
      assert(testpilot_subject && typeof testpilot_subject === 'object', 'testpilot_subject module missing or not an object');
      assert(testpilot_subject.file_0001 && typeof testpilot_subject.file_0001 === 'object', 'testpilot_subject.file_0001 missing or not an object');
      // Accept either object or function for FsWatcherService (some modules export a function/class)
      assert(
        testpilot_subject.file_0001.FsWatcherService &&
        (typeof testpilot_subject.file_0001.FsWatcherService === 'object' || typeof testpilot_subject.file_0001.FsWatcherService === 'function'),
        'FsWatcherService missing or not an object/function'
      );
      svc = testpilot_subject.file_0001.FsWatcherService.None;
      assert(svc, 'FsWatcherService.None missing');
      assert.strictEqual(typeof svc.dispose, 'function', 'dispose is not a function on FsWatcherService.None');
    });

    // Helper that calls dispose and returns a Promise that resolves with the returned value
    function callDispose() {
      try {
        const result = svc.dispose();
        if (result && typeof result.then === 'function') {
          return result;
        }
        return Promise.resolve(result);
      } catch (err) {
        return Promise.reject(err);
      }
    }

    it('should expose dispose as a function', function() {
      assert.strictEqual(typeof svc.dispose, 'function');
    });

        })
})