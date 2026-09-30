let mocha = require('mocha');
let assert = require('assert');

// Safely try to require the real module, but tests below are self-contained
// and will use stubs so they don't rely on any external resources.
let testpilot_subject;
try {
  testpilot_subject = require('..');
} catch (e) {
  testpilot_subject = null;
}

// Helper to build a stub shaped like the target structure:
// testpilot_subject.file_0001.FsWatcherService.$di$dependencies[1].id
function makeStub(idValue) {
  return {
    file_0001: {
      FsWatcherService: {
        // first dependency at index 0 is arbitrary, index 1 holds our idValue
        $di$dependencies: [
          { id: 'ignored' },
          { id: idValue },
        ],
      },
    },
  };
}

describe('test testpilot_subject', function() {
  // A collection of id values and their expected toString() results.
  const cases = [
    { name: 'number id', id: 123, expected: '123' },
    // Use a BigInt value within the safe integer range to avoid precision loss
    { name: 'bigint id', id: BigInt(9007199254740991), expected: '9007199254740991' },
    { name: 'symbol id', id: Symbol('sym'), expected: 'Symbol(sym)' },
    { name: 'object with custom toString', id: { toString() { return 'custom-id'; } }, expected: 'custom-id' },
  ];

  cases.forEach(function(tc) {
    it(`testpilot_subject.file_0001.FsWatcherService.$di$dependencies[1].id.toString - ${tc.name}`, function() {
      const stub = makeStub(tc.id);
      const result = stub.file_0001.FsWatcherService.$di$dependencies[1].id.toString();
      assert.strictEqual(result, tc.expected);
    });
  });

  })