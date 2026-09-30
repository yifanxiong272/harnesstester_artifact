let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.setExpanded', function() {
        it('exists and is a function', function() {
            let proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
            assert.ok(proto, 'prototype should exist');
            assert.strictEqual(typeof proto.setExpanded, 'function', 'setExpanded should be a function');
        });

            })
})