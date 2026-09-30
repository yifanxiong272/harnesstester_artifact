let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep backups of original prototype methods so we can restore them after tests
    const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
    const original = {
        buildCallPreview: proto.buildCallPreview,
        buildProgressBlock: proto.buildProgressBlock,
        buildDetachHintBlock: proto.buildDetachHintBlock,
        buildLiveOutputBlock: proto.buildLiveOutputBlock,
        buildContent: proto.buildContent,
        buildSubagentBlock: proto.buildSubagentBlock
    };

    // Helper to create an instance safely (some constructors may expect args)
    function makeInstance() {
        try {
            return new testpilot_subject.file_0003.ToolCallComponent();
        } catch (e) {
            // fallback to plain object with correct prototype
            return Object.create(testpilot_subject.file_0003.ToolCallComponent.prototype);
        }
    }

    afterEach(function() {
        // restore original prototype methods
        proto.buildCallPreview = original.buildCallPreview;
        proto.buildProgressBlock = original.buildProgressBlock;
        proto.buildDetachHintBlock = original.buildDetachHintBlock;
        proto.buildLiveOutputBlock = original.buildLiveOutputBlock;
        proto.buildContent = original.buildContent;
        proto.buildSubagentBlock = original.buildSubagentBlock;
    });

    it('rebuildBody should trim children to two elements before rebuilding and then append the blocks in order', function() {
        // Arrange
        const instance = makeInstance();
        // Start with more than two children to test trimming
        instance.children = ['first', 'second', 'third', 'fourth', 'fifth'];

        // Stubs that append markers so we can assert final children and order
        proto.buildCallPreview = function() { this.children.push('callPreview'); };
        proto.buildProgressBlock = function() { this.children.push('progress'); };
        proto.buildDetachHintBlock = function() { this.children.push('detachHint'); };
        proto.buildLiveOutputBlock = function() { this.children.push('liveOutput'); };
        proto.buildContent = function() { this.children.push('content'); };
        proto.buildSubagentBlock = function() { this.children.push('subagent'); };

        // Act
        instance.rebuildBody();

        // Assert
        // The original extra children beyond the first two should have been removed
        assert.strictEqual(instance.children[0], 'first');
        assert.strictEqual(instance.children[1], 'second');

        // The appended sequence should follow exactly after the first two
        const expected = ['callPreview','progress','detachHint','liveOutput','content','subagent'];
        assert.deepStrictEqual(instance.children.slice(2), expected);

        // callPreviewEndIndex should mark the index immediately after buildCallPreview was run
        // buildCallPreview pushed one element after the two originals, so it should be 3
        assert.strictEqual(instance.callPreviewEndIndex, 3);
    });

    })