let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0003.ToolCallComponent.prototype.markBackgrounded', function() {
    it('sets detached flag, updates phase, updates header, rebuilds content, notifies snapshot, and requests render when ui present', function() {
      const fn = testpilot_subject.file_0003.ToolCallComponent.prototype.markBackgrounded;
      assert.strictEqual(typeof fn, 'function', 'markBackgrounded should be a function');

      let calls = { setText: 0, rebuild: 0, notify: 0, render: 0, lastText: null };

      const mock = {
        detachedFromForeground: false,
        subagentPhase: 'foreground',
        headerText: {
          setText: (t) => { calls.setText++; calls.lastText = t; }
        },
        buildHeader: () => 'built-header',
        rebuildContent: () => { calls.rebuild++; },
        notifySnapshotChange: () => { calls.notify++; },
        ui: {
          requestRender: () => { calls.render++; }
        }
      };

      // invoke the prototype method with our mock this
      fn.call(mock);

      // verify state changes
      assert.strictEqual(mock.detachedFromForeground, true, 'detachedFromForeground should be set to true');
      assert.strictEqual(mock.subagentPhase, 'backgrounded', 'subagentPhase should be "backgrounded"');

      // verify helper calls
      assert.strictEqual(calls.setText, 1, 'headerText.setText should be called once');
      assert.strictEqual(calls.lastText, 'built-header', 'headerText.setText should be called with the result of buildHeader');
      assert.strictEqual(calls.rebuild, 1, 'rebuildContent should be called once');
      assert.strictEqual(calls.notify, 1, 'notifySnapshotChange should be called once');
      assert.strictEqual(calls.render, 1, 'ui.requestRender should be called once when ui is present');
    });

        })
})