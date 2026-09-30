let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the prototype function so we can call it with controlled "this"
    const updateToolCall = testpilot_subject.file_0003.ToolCallComponent.prototype.updateToolCall;

    it('sets this.toolCall and calls lifecycle methods in the expected order when ui is present', function() {
        // Prepare a fake instance with spies and an event log to capture call order
        const events = [];
        const fakeToolCall = { id: 42, name: 'example' };

        const fakeInstance = {
            // toolCall should be set by the method
            toolCall: null,
            // record that syncStreamingProgressTimer was called and observe this.toolCall at that time
            syncStreamingProgressTimer: function() {
                events.push('sync:' + (this.toolCall ? this.toolCall.id : 'no-tool'));
            },
            // buildHeader should be called to produce the header text
            buildHeader: function() {
                events.push('buildHeader');
                return 'HEADER-' + (this.toolCall ? this.toolCall.name : 'none');
            },
            // headerText.setText should receive the header returned by buildHeader
            headerText: {
                lastText: null,
                setText: function(txt) {
                    this.lastText = txt;
                    // push to outer events array to keep ordering
                    events.push('setText:' + txt);
                }
            },
            // rebuildBody and notifySnapshotChange should be called
            rebuildBody: function() {
                events.push('rebuildBody');
            },
            notifySnapshotChange: function() {
                events.push('notifySnapshotChange');
            },
            // ui exists and has requestRender
            ui: {
                requested: false,
                requestRender: function() {
                    this.requested = true;
                    events.push('requestRender');
                }
            }
        };

        // Call the prototype method with our fake instance as `this`
        updateToolCall.call(fakeInstance, fakeToolCall);

        // Verify that the toolCall property was set
        assert.strictEqual(fakeInstance.toolCall, fakeToolCall);

        // Verify headerText received the built header
        assert.strictEqual(fakeInstance.headerText.lastText, 'HEADER-example');

        // Verify ui.requestRender was called
        assert.strictEqual(fakeInstance.ui.requested, true);

        // Verify lifecycle method call order matches the implementation:
        // 1. syncStreamingProgressTimer (records sync:id)
        // 2. buildHeader
        // 3. headerText.setText
        // 4. rebuildBody
        // 5. notifySnapshotChange
        // 6. ui.requestRender
        assert.deepStrictEqual(events, [
            'sync:42',
            'buildHeader',
            'setText:HEADER-example',
            'rebuildBody',
            'notifySnapshotChange',
            'requestRender'
        ]);
    });

    })