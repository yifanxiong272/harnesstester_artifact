let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const writeRaw = testpilot_subject.file_0002.OutputManager.prototype.writeRaw;

    it('calls stdout.write with the provided text when not disabled', function() {
        let captured = '';
        const om = {
            disabled: false,
            stdout: {
                write: function(text) { captured += text; }
            }
        };

        // call the prototype method with our fake instance
        writeRaw.call(om, 'hello world');

        assert.strictEqual(captured, 'hello world');
    });

    })