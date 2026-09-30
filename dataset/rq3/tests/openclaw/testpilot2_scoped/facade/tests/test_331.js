let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0013.ensureDockerImage (input validation)', function() {
        it('should reject when called with no arguments', async function() {
            await assert.rejects(
                async () => { await testpilot_subject.file_0013.ensureDockerImage(); },
                Error
            );
        });

            })
})