let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0008.detectCursorKeyMode', function() {
        let detect = testpilot_subject.file_0008.detectCursorKeyMode;

        it('should produce same detection for application vs normal sequences', function() {
            let app = detect(Buffer.from([0x1b, 0x4f, 0x41]));
            let normal = detect(Buffer.from([0x1b, 0x5b, 0x41]));

            // The two modes should be reported the same
            assert.strictEqual(app, normal, 'Application and normal cursor-key modes should be detected the same');
        });

    })
})