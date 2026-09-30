let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const proto = testpilot_subject &&
                  testpilot_subject.file_0003 &&
                  testpilot_subject.file_0003.ToolCallComponent &&
                  testpilot_subject.file_0003.ToolCallComponent.prototype;

    it('should clear a non-numeric (object) handle and set detachHintTimer to null', function() {
        if (!proto || typeof proto.stopDetachHintTimer !== 'function') this.skip();

        const originalClear = global.clearTimeout;
        let called = [];
        global.clearTimeout = function(id) { called.push(id); };

        try {
            const fakeHandle = { handle: 'fake' };
            const obj = Object.create(proto);
            obj.detachHintTimer = fakeHandle;

            proto.stopDetachHintTimer.call(obj);

            // ensure whatever was stored is passed to clearTimeout and then cleared
            assert.deepStrictEqual(called, [fakeHandle]);
            // allow either null or undefined (some implementations delete the property)
            assert.ok(obj.detachHintTimer == null);
        } finally {
            global.clearTimeout = originalClear;
        }
    });
});