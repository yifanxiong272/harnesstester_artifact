let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0003.ToolCallComponent.prototype.dispose - calls all stop timers once and returns undefined', function(done) {
        const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        // create an instance without calling constructor to avoid side-effects
        const inst = Object.create(proto);

        let calls = { stream: 0, sub: 0, detach: 0 };
        inst.stopStreamingProgressTimer = function() { calls.stream++; };
        inst.stopSubagentElapsedTimer = function() { calls.sub++; };
        inst.stopDetachHintTimer = function() { calls.detach++; };

        const ret = inst.dispose();

        // dispose should return undefined
        assert.strictEqual(ret, undefined);
        // each stop* timer should be called exactly once
        assert.strictEqual(calls.stream, 1);
        assert.strictEqual(calls.sub, 1);
        assert.strictEqual(calls.detach, 1);
        done();
    });

    })