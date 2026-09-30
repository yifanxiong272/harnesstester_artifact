let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  describe('file_0002.FsSearchService.None.dispose', function() {
    it('should exist and be a function', function() {
      // ensure the path exists
      assert.ok(testpilot_subject, 'module missing: testpilot_subject');
      assert.ok(testpilot_subject.file_0002, 'module missing: file_0002');
      assert.ok(testpilot_subject.file_0002.FsSearchService, 'module missing: FsSearchService');
      assert.ok(testpilot_subject.file_0002.FsSearchService.None, 'module missing: None');

      const dispose = testpilot_subject.file_0002.FsSearchService.None.dispose;
      assert.strictEqual(typeof dispose, 'function', 'dispose should be a function');
    });

        })
})