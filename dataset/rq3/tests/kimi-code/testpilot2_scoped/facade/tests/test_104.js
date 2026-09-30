let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.KimiCore.prototype.getCoreInfo - returns object with version property', function() {
        // Call the prototype method directly (it does not rely on `this`)
        const info = testpilot_subject.file_0002.KimiCore.prototype.getCoreInfo.call({});
        assert.strictEqual(typeof info, 'object', 'getCoreInfo should return an object');
        assert.ok(Object.prototype.hasOwnProperty.call(info, 'version'), 'returned object should have a "version" property');
    });

    })