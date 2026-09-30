let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0015.processAiSdkStreamPart', function() {
        const fn = testpilot_subject.file_0015.processAiSdkStreamPart;

        it('yields text for "text" and "text-delta" parts', function() {
            let iter = fn({type: "text", text: "Hello"});
            let r = iter.next();
            assert.deepStrictEqual(r, { value: { type: "text", text: "Hello" }, done: false });
            assert.deepStrictEqual(iter.next(), { value: undefined, done: true });

            iter = fn({type: "text-delta", text: "Partial"});
            r = iter.next();
            assert.deepStrictEqual(r, { value: { type: "text", text: "Partial" }, done: false });
            assert.deepStrictEqual(iter.next(), { value: undefined, done: true });
        });

            })
})