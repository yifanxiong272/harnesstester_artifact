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

    it('updates counts when listeners are removed', function() {
        const E = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
        // Provide a string name to satisfy AsyncResource/constructor requirements
        const inst = new E('EventEmitterAsyncResource');

        const add = getAddMethod(inst);
        const remove = getRemoveMethod(inst);
        assert.ok(add, 'No add/on/addListener method found on EventEmitterAsyncResource');
        assert.ok(remove, 'No remove/off/removeListener method found on EventEmitterAsyncResource');

        function a() {}
        function b() {}

        add.call(inst, 'evt', a);
        add.call(inst, 'evt', b);
        assert.strictEqual(inst.listenerCount('evt'), 2, 'Should start with 2 listeners');

        // remove one listener
        remove.call(inst, 'evt', a);
        assert.strictEqual(inst.listenerCount('evt'), 1, 'Should have 1 listener after removing one');

        // remove the other
        remove.call(inst, 'evt', b);
        assert.strictEqual(inst.listenerCount('evt'), 0, 'Should have 0 listeners after removing both');
    });
});