let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.OutputManager.prototype.isAlreadyDisplayed', function() {
        const proto = testpilot_subject.file_0002.OutputManager.prototype;

        it('returns false when there is no entry for the timestamp', function() {
            const om = Object.create(proto);
            om.displayedMessages = new Map(); // empty map, no entry for 'ts-1'
            assert.strictEqual(om.isAlreadyDisplayed('ts-1'), false);
        });

            })
})