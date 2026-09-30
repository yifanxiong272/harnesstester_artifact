let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0002.KimiCore.prototype.cancelGoal', function() {
    it('calls sessionApi with sessionId and returns the non-promise cancelGoal result, passing only the rest payload', function() {
      // create a fake "this" with a sessionApi that records inputs and returns an object
      let calledSessionId = null;
      let receivedPayload = null;
      const fakeThis = {
        sessionApi: function(sessionId) {
          calledSessionId = sessionId;
          return {
            cancelGoal: function(payload) {
              receivedPayload = payload;
              return 'sync-result';
            }
          };
        }
      };

      return testpilot_subject.file_0002.KimiCore.prototype.cancelGoal.call(
        fakeThis,
        { sessionId: 'session-123', alpha: 1, beta: 2 }
      ).then(result => {
        assert.strictEqual(calledSessionId, 'session-123', 'sessionApi should be called with the sessionId');
        // payload passed to cancelGoal should not contain sessionId because of the destructuring in the implementation
        assert.deepStrictEqual(receivedPayload, { alpha: 1, beta: 2 }, 'payload should be the rest object without sessionId');
        assert.strictEqual(result, 'sync-result', 'should return the value returned by cancelGoal wrapped by Promise.resolve');
      });
    });

        })
})