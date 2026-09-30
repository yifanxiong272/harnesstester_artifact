let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case some implementations take longer
    this.timeout(5000);

    // Basic existence checks and type checks
    it('exports file_0011.generateImageWithImagesApi as a function', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0011, 'module.file_0011 should be present');
        assert.strictEqual(
            typeof testpilot_subject.file_0011.generateImageWithImagesApi,
            'function',
            'generateImageWithImagesApi should be a function'
        );
    });

    // Verify that calling the function returns a Promise-like object when given an options object.
    })