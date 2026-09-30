let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.OutputManager.prototype.markDisplayed - stores message in displayedMessages Map', function(done) {
        // Get the prototype so we don't need to call the real constructor (which might have side effects)
        const OMProto = testpilot_subject.file_0002.OutputManager.prototype;
        // Create a plain object that inherits the prototype
        const om = Object.create(OMProto);

        // Ensure displayedMessages is a Map-like object (method uses .set)
        om.displayedMessages = new Map();

        const ts = 123;
        const text = 'hello world';
        const partial = false;

        const ret = om.markDisplayed(ts, text, partial);

        // method does not return anything
        assert.strictEqual(ret, undefined);

        // The entry should be present in the Map
        assert.strictEqual(om.displayedMessages.has(ts), true);
        const stored = om.displayedMessages.get(ts);
        assert.deepStrictEqual(stored, { ts, text, partial });

        done();
    });

    })