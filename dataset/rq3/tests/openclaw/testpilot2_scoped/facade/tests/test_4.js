let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0001.classifyFailoverReasonFromHttpStatus', function() {
    const fn = testpilot_subject.file_0001.classifyFailoverReasonFromHttpStatus;

    // helper that supports sync return values or Promises
    function invoke(status, message) {
      try {
        const res = fn(status, message);
        if (res && typeof res.then === 'function') {
          return res;
        }
        return Promise.resolve(res);
      } catch (err) {
        return Promise.reject(err);
      }
    }

    it('does not throw and returns either a string or null for a variety of inputs', async function() {
      const inputs = [
        [200, 'OK'],
        ['200', 'OK as string status'],
        [404, 'Not Found'],
        [500, 'Internal Server Error'],
        [503, 'Service Unavailable'],
        [0, 'Zero status'],
        [null, null],
        [undefined, undefined],
        [NaN, 'NaN'],
        [{}, 'object status'],
        [[], 'array status'],
        [-1, 'negative'],
      ];

      for (const [status, message] of inputs) {
        const out = await invoke(status, message);
        assert.ok(
          out === null || typeof out === 'string',
          `expected null or string, got ${typeof out} for status=${JSON.stringify(status)} message=${JSON.stringify(message)}`
        );
      }
    });

        })
})