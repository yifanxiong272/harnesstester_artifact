let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to create an OutputManager-like object without calling its constructor
    function makeOM() {
        const proto = testpilot_subject.file_0002.OutputManager.prototype;
        const om = Object.create(proto);

        // required internal state
        om.displayedMessages = new Map();
        om.streamedContent = new Map();

        // spies / stubs for methods the tested method may call
        om._streamContentCalls = [];
        om.streamContent = function(ts, text, tag) {
            this._streamContentCalls.push([ts, text, tag]);
            // do not modify streamedContent unless test wants to explicitly set it
        };

        om._writeRawCalls = [];
        om.writeRaw = function(delta) {
            this._writeRawCalls.push(delta);
        };

        om._finishStreamCalls = [];
        om.finishStream = function(ts) {
            this._finishStreamCalls.push(ts);
            // simulate cleaning up streamedContent like a real implementation might
            this.streamedContent.delete(ts);
        };

        om._outputCalls = [];
        om.output = function(prefix, text) {
            this._outputCalls.push([prefix, text]);
        };

        return om;
    }

    it('calls streamContent and marks displayedMessages.partial when isPartial && text', function() {
        const om = makeOM();
        const ts = 'ts-1';
        const text = 'partial reasoning';
        om.outputReasoningMessage(ts, text, true, false);

        // streamContent should be called once with the reasoning tag
        assert.strictEqual(om._streamContentCalls.length, 1);
        assert.deepStrictEqual(om._streamContentCalls[0], [ts, text, '[reasoning]']);

        // displayedMessages should record the partial message
        const recorded = om.displayedMessages.get(ts);
        assert.ok(recorded, 'displayedMessages should contain the ts key');
        assert.strictEqual(recorded.partial, true);
        assert.strictEqual(recorded.text, text);

        // ensure no final output/write happened
        assert.strictEqual(om._writeRawCalls.length, 0);
        assert.strictEqual(om._finishStreamCalls.length, 0);
        assert.strictEqual(om._outputCalls.length, 0);
    });

    })