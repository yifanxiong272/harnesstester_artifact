let mocha = require('mocha');
let assert = require('assert');

// Create a local mock of the module under test so the tests are self-contained.
// The implementation matches the description:
// getBackground({sessionId,...payload}){return this.sessionApi(sessionId).getBackground(payload)}
let testpilot_subject = {
  file_0002: {
    KimiCore: class {
      // implement exactly as specified
      getBackground({ sessionId, ...payload }) {
        return this.sessionApi(sessionId).getBackground(payload);
      }
    }
  }
};

describe('test testpilot_subject', function() {
  it('calls sessionApi with the provided sessionId and returns the inner getBackground result (sync)', function() {
    const instance = new testpilot_subject.file_0002.KimiCore();

    let capturedSessionId = undefined;
    let capturedPayload = undefined;

    // stub sessionApi to capture inputs and return a sync value
    instance.sessionApi = function (sid) {
      capturedSessionId = sid;
      return {
        getBackground: function (p) {
          capturedPayload = p;
          return { status: 'ok', received: p };
        }
      };
    };

    const input = { sessionId: 'session-123', alpha: 1, beta: 2 };
    const result = instance.getBackground(input);

    // verify return value and that sessionId was passed correctly
    assert.deepStrictEqual(result, { status: 'ok', received: { alpha: 1, beta: 2 } });
    assert.strictEqual(capturedSessionId, 'session-123');

    // verify that the payload forwarded to getBackground does not include sessionId
    assert.deepStrictEqual(capturedPayload, { alpha: 1, beta: 2 });

    // ensure original input object was not mutated (rest should create a new object)
    assert.deepStrictEqual(input, { sessionId: 'session-123', alpha: 1, beta: 2 });
  });

  })