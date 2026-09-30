let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to obtain add/remove methods safely
    function getAddMethod(inst) {
        return inst.on || inst.addListener || inst.add || null;
    }
    function getRemoveMethod(inst) {
        return inst.removeListener || inst.off || inst.remove || null;
    }

    it('counts listeners added via on/addListener and can count occurrences of a specific listener', function() {
        const E = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
        // Provide a name option so constructor doesn't receive undefined for options.name
        const inst = new E({ name: 'EventEmitterAsyncResource' });

        const add = getAddMethod(inst);
        assert.ok(add, 'No add/on/addListener method found on EventEmitterAsyncResource');

        function handler() {}
        // add the same handler twice
        add.call(inst, 'my-event', handler);
        add.call(inst, 'my-event', handler);

        // total listeners for the event should be 2
        assert.strictEqual(inst.listenerCount('my-event'), 2, 'Expected 2 listeners for my-event');

        // counting a particular listener should return how many times that exact function was added
        assert.strictEqual(inst.listenerCount('my-event', handler), 2, 'Expected listenerCount with specific handler to be 2');

        // a different function should count as 0
        assert.strictEqual(inst.listenerCount('my-event', function() {}), 0, 'Different function should not be counted');
    });

    })