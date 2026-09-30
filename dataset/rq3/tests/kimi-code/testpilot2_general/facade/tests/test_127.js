let mocha = require('mocha');
let assert = require('assert');

// Prepare stubs for module-level imports used by testpilot_subject
// These must be in place before requiring the module under test.
global.import_pi_tui = {
  // Simple Text constructor that records received args for assertions
  Text: function (content, a, b) {
    this.content = content;
    this.a = a;
    this.b = b;
  }
};

let dimCalled = false;
let dimArg = undefined;
global.import_theme = {
  currentTheme: {
    // Record that dim was called and return a predictable transformed string.
    dim: function (s) {
      dimCalled = true;
      dimArg = s;
      return 'dimmed:' + String(s);
    }
  }
};

// Now require the module under test
let testpilot_subject = require('..');

describe('testpilot_subject.file_0003.ToolCallComponent.prototype.buildDetachHintBlock', function () {
  // Helper to create a minimal instance whose prototype is the real prototype,
  // but whose state we control.
  function makeInstance() {
    const Proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
    const inst = Object.create(Proto);
    // default spy for addChild
    inst.addChildCalled = 0;
    inst.addChildArgs = [];
    inst.addChild = function (arg) {
      this.addChildCalled++;
      this.addChildArgs.push(arg);
    };
    // default flags
    inst.detachHintVisible = false;
    // no result by default (explicitly undefined)
    if ('result' in inst) delete inst.result;
    return inst;
  }

  beforeEach(function () {
    // reset dim spy state before each test
    dimCalled = false;
    dimArg = undefined;
  });

  it('does nothing when detachHintVisible is false', function () {
    const inst = makeInstance();
    inst.detachHintVisible = false;
    // ensure result is undefined
    delete inst.result;

    inst.buildDetachHintBlock();

    assert.strictEqual(inst.addChildCalled, 0, 'addChild should not be called when detachHintVisible is false');
    assert.strictEqual(dimCalled, false, 'dim should not be called when detachHintVisible is false');
  });

  })