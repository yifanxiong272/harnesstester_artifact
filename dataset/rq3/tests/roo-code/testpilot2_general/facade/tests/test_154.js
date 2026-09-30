let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const finishStream = testpilot_subject.file_0002.OutputManager.prototype.finishStream;

    it('calls writeRaw, clears currentlyStreamingTs, and emits streamingState.next when ts matches', function(done) {
        let writeCalls = [];
        let nextCalls = [];

        const ctx = {
            currentlyStreamingTs: 42,
            writeRaw: function(s) { writeCalls.push(s); },
            streamingState: {
                next: function(v) { nextCalls.push(v); }
            }
        };

        finishStream.call(ctx, 42);

        // writeRaw should be called once with newline
        assert.strictEqual(writeCalls.length, 1);
        assert.strictEqual(writeCalls[0], "\n");

        // currentlyStreamingTs should be cleared
        assert.strictEqual(ctx.currentlyStreamingTs, null);

        // streamingState.next should be called once with expected payload
        assert.strictEqual(nextCalls.length, 1);
        assert.deepStrictEqual(nextCalls[0], { ts: null, isStreaming: false });

        done();
    });

    })