let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0002.KimiCore.prototype.pauseGoal', function() {

    it('resolves with value when sessionApi.pauseGoal returns a plain value', function() {
      const KimiCore = testpilot_subject.file_0002.KimiCore;
      // create an instance without running constructor to avoid external side effects
      const instance = Object.create(KimiCore.prototype);

      let seenSessionId = null;
      let seenPayload = null;
      instance.sessionApi = function(sessionId) {
        seenSessionId = sessionId;
        return {
          pauseGoal: function(payload) {
            seenPayload = payload;
            return 'OK';
          }
        };
      };

      return instance.pauseGoal({ sessionId: 's1', a: 1 }).then(result => {
        assert.strictEqual(result, 'OK');
        assert.strictEqual(seenSessionId, 's1');
        assert.deepStrictEqual(seenPayload, { a: 1 });
      });
    });

        })
})