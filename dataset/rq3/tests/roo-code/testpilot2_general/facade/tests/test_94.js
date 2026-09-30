let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
const { Writable } = require('stream');

describe('test testpilot_subject', function() {
    // helper to create a writable stream that captures written data
    function createCapture() {
        let s = '';
        const w = new Writable({
            write(chunk, encoding, callback) {
                s += chunk.toString();
                callback();
            }
        });
        w.get = () => s;
        return w;
    }

    it('writes to stdout and stderr using output and outputError', function() {
        const stdout = createCapture();
        const stderr = createCapture();
        const om = new testpilot_subject.file_0002.OutputManager({ stdout, stderr });

        om.output('[info]', 'all good');
        om.outputError('[err]', 'something went wrong');

        assert.strictEqual(stdout.get(), '[info] all good\n');
        assert.strictEqual(stderr.get(), '[err] something went wrong\n');
    });

    })