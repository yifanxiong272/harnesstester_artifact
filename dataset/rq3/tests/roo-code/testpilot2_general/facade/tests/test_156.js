let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0002.OutputManager.prototype.outputCompletionSayMessage', function() {

    function makeManager() {
        const mgr = new testpilot_subject.file_0002.OutputManager();
        // ensure maps/flags exist and are fresh
        mgr.displayedMessages = new Map();
        mgr.streamedContent = new Map();
        mgr.completionResultStreamed = false;

        // Spy containers
        mgr._calls = {
            streamContent: [],
            writeRaw: [],
            finishStream: [],
            output: []
        };

        // Replace methods with spies
        mgr.streamContent = function(ts, text, role) {
            this._calls.streamContent.push({ts, text, role});
        };
        mgr.writeRaw = function(delta) {
            this._calls.writeRaw.push(delta);
        };
        mgr.finishStream = function(ts) {
            this._calls.finishStream.push(ts);
        };
        mgr.output = function(prefix, text) {
            this._calls.output.push({prefix, text});
        };

        return mgr;
    }

    it('streams partial text, records displayedMessages and sets completionResultStreamed', function() {
        const mgr = makeManager();
        const ts = 't1';
        const text = 'partial text';

        mgr.outputCompletionSayMessage(ts, text, true, false);

        // streamContent called once with [assistant] role
        assert.strictEqual(mgr._calls.streamContent.length, 1);
        assert.deepStrictEqual(mgr._calls.streamContent[0], {ts, text, role: "[assistant]"});

        // no writeRaw/finishStream/output called
        assert.strictEqual(mgr._calls.writeRaw.length, 0);
        assert.strictEqual(mgr._calls.finishStream.length, 0);
        assert.strictEqual(mgr._calls.output.length, 0);

        // displayedMessages updated with partial:true
        assert.strictEqual(mgr.displayedMessages.has(ts), true);
        assert.deepStrictEqual(mgr.displayedMessages.get(ts), {ts, text, partial: true});

        // flag set
        assert.strictEqual(mgr.completionResultStreamed, true);
    });

    })