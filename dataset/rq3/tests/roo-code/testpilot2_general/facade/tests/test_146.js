let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('skipFirstUserMessage: records displayed message and does not call output/stream/write/finish', function(done) {
        const OM = testpilot_subject.file_0002.OutputManager;
        const mgr = new OM();

        // ensure fresh maps
        mgr.displayedMessages = new Map();
        mgr.streamedContent = new Map();

        let called = {stream:false,output:false,writeRaw:false,finish:false};

        mgr.streamContent = function(){ called.stream = true; };
        mgr.output = function(){ called.output = true; };
        mgr.writeRaw = function(){ called.writeRaw = true; };
        mgr.finishStream = function(){ called.finish = true; };

        const ts = 'ts-skip-1';
        mgr.outputTextMessage(ts, 'user message', false, false, true);

        // displayedMessages should contain the entry and no other actions taken
        assert.strictEqual(mgr.displayedMessages.size, 1);
        const entry = mgr.displayedMessages.get(ts);
        assert.ok(entry, 'displayedMessages entry missing');
        assert.strictEqual(entry.ts, ts);
        assert.strictEqual(entry.text, 'user message');
        assert.strictEqual(entry.partial, false);

        assert.strictEqual(called.stream, false);
        assert.strictEqual(called.output, false);
        assert.strictEqual(called.writeRaw, false);
        assert.strictEqual(called.finish, false);

        done();
    });

    })