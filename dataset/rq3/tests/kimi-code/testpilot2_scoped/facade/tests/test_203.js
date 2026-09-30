let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  const fn = testpilot_subject.file_0002.KimiCore.prototype.undoHistory;

  it('forwards sessionId and payload and returns sync result', function() {
    let captured = {};
    const ctx = {
      sessionApi(sessionId) {
        captured.sessionId = sessionId;
        return {
          undoHistory(payload) {
            captured.payload = payload;
            return 'sync-result';
          }
        };
      }
    };

    const res = fn.call(ctx, { sessionId: 's123', alpha: 1, beta: 2 });

    assert.strictEqual(res, 'sync-result');
    assert.strictEqual(captured.sessionId, 's123');
    assert.deepStrictEqual(captured.payload, { alpha: 1, beta: 2 });
  });

  })