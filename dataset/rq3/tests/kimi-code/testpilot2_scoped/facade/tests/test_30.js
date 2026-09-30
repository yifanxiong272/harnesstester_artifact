let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  describe('file_0001.FsWatcherService.None.dispose', function() {
    it('should export an object "None" with a "dispose" function', function() {
      const svc = testpilot_subject && testpilot_subject.file_0001 && testpilot_subject.file_0001.FsWatcherService;
      assert.ok(svc, 'FsWatcherService should be exported');
      const none = svc.None;
      assert.ok(typeof none === 'object' || typeof none === 'function', 'None should be an object (or function)');
      assert.strictEqual(typeof none.dispose, 'function', 'dispose should be a function');
    });

        })
})