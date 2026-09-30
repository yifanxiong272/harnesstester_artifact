let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype.getCredentials', function() {

    it('returns the exact object assigned to credentials', function() {
      const Manager = testpilot_subject.file_0001.OpenAiCodexOAuthManager;
      const mgr = new Manager();
      const creds = { token: 'abc', scope: ['a'] };
      mgr.credentials = creds;
      assert.strictEqual(mgr.getCredentials(), creds);
    });

        })
})