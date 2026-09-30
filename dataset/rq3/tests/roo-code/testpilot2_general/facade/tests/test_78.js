let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0001.isTokenExpired', function() {
    const BUFFER_MS = 5 * 60 * 1e3; // 5 minutes in ms
    let originalDateNow;

    beforeEach(function() {
      // save original Date.now so tests can stub it
      originalDateNow = Date.now;
    });

    afterEach(function() {
      // restore Date.now after each test
      Date.now = originalDateNow;
    });

    it('returns true for an already expired token', function() {
      const fixedNow = 1600000000000;
      Date.now = () => fixedNow;
      const credentials = { expires: fixedNow - 1000 }; // expired 1s ago
      assert.strictEqual(testpilot_subject.file_0001.isTokenExpired(credentials), true);
    });

        })
})