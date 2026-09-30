let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('testpilot_subject.file_0007.MessageProcessor.prototype.setDebug', function() {

        it('sets options.debug to true when called on an instance created from the prototype', function() {
            let Proto = testpilot_subject.file_0007.MessageProcessor.prototype;
            // create an "instance" without calling any constructor
            let instance = Object.create(Proto);
            instance.options = { debug: false };

            // method is on the prototype
            instance.setDebug(true);

            assert.strictEqual(instance.options.debug, true);
        });

            })
})