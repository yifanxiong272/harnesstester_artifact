let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
const EventEmitter = require('events').EventEmitter;

describe('test testpilot_subject', function() {
    it('emitNewMessageEvents emits only the last message in the array', function(done) {
        const MP = testpilot_subject.file_0007.MessageProcessor;
        const mp = new MP();
        mp.emitter = new EventEmitter();

        const messages = [{text: 'first'}, {text: 'second'}, {text: 'last'}];
        let calls = 0;

        mp.emitter.on('message', function(msg) {
            calls++;
            // should receive exactly the last message object
            assert.strictEqual(msg, messages[messages.length - 1]);
        });

        mp.emitNewMessageEvents(null, null, messages);

        // emission is synchronous, so listener already ran
        assert.strictEqual(calls, 1);
        done();
    });

    })