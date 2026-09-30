let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const OutputManagerProto = testpilot_subject.file_0002.OutputManager.prototype;

    function makeMockStdout() {
        return {
            writes: [],
            write: function(s) { this.writes.push(s); }
        };
    }

    it('writes "label text\\n" when text is provided', function(done) {
        const mockStdout = makeMockStdout();
        const manager = { disabled: false, stdout: mockStdout };

        OutputManagerProto.output.call(manager, 'LABEL', 'TEXT');

        assert.strictEqual(mockStdout.writes.length, 1);
        assert.strictEqual(mockStdout.writes[0], 'LABEL TEXT\n');
        done();
    });

    })