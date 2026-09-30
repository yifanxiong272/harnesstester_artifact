let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Ensure the imported dependencies used by the method are available on the module export
    beforeEach(function() {
        // Provide a minimal ShellExecutionComponent constructor that records the options it was constructed with
        testpilot_subject.import_shell_execution = {
            ShellExecutionComponent: function(opts) {
                // store the passed options so tests can inspect them
                this.opts = opts;
            }
        };
        // Provide a result preview lines constant used by the method
        testpilot_subject.import_rendering = {
            RESULT_PREVIEW_LINES: 7
        };
    });

    it('does nothing if this.result is already defined', function() {
        const build = testpilot_subject.file_0003.ToolCallComponent.prototype.buildLiveOutputBlock;
        let added = [];
        // create a minimal "this" context
        let ctx = {
            result: {}, // non-undefined => should cause early return
            liveOutput: ['line1', 'line2'],
            addChild: function(child) { added.push(child); },
            toolCall: { id: 42 },
            expanded: true
        };

        // Call the method with our context
        build.call(ctx);

        // Expect no child was added
        assert.strictEqual(added.length, 0);
    });

    })