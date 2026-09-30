let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should write header and full text when no previous content for ts', function(done) {
        // Create an instance without running any constructor logic by using prototype
        const om = Object.create(testpilot_subject.file_0002.OutputManager.prototype);

        // Provide the minimal fields the method expects
        om.streamedContent = new Map();
        const writes = [];
        om.writeRaw = function(s) { writes.push(s); };
        const nextCalls = [];
        om.streamingState = { next: function(arg) { nextCalls.push(arg); } };
        om.currentlyStreamingTs = null;

        const ts = 123;
        const header = "HEADER";
        const text = "hello world";

        // Call the method under test
        om.streamContent(ts, text, header);

        // Assertions
        // First writeRaw call should be newline + header + space
        assert.strictEqual(writes.length, 2, 'expected two writeRaw calls (header and text)');
        assert.strictEqual(writes[0], `\n${header} `, 'first writeRaw should write header with leading newline and trailing space');
        assert.strictEqual(writes[1], text, 'second writeRaw should write the full text');

        // streamedContent should have an entry for ts with correct values
        const entry = om.streamedContent.get(ts);
        assert.ok(entry, 'streamedContent must contain an entry for the ts');
        assert.strictEqual(entry.ts, ts);
        assert.strictEqual(entry.text, text);
        assert.strictEqual(entry.headerShown, true);

        // currentlyStreamingTs should be set and streamingState.next should have been called
        assert.strictEqual(om.currentlyStreamingTs, ts);
        assert.strictEqual(nextCalls.length, 1, 'streamingState.next should be called once');
        assert.deepStrictEqual(nextCalls[0], { ts, isStreaming: true });

        done();
    });

    })