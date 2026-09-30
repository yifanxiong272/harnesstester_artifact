let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0001.generateCodeChallenge', function() {
    it('should produce the RFC 7636 example code challenge', function() {
      // Example taken from RFC 7636
      const verifier = 'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk';
      const expected = 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM';
      const out = testpilot_subject.file_0001.generateCodeChallenge(verifier);
      assert.strictEqual(out, expected);
    });

        })
})