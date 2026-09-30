let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fns = testpilot_subject.file_0012;
    const sut = fns.sanitizeToolResultImages;

    // Keep original helpers to restore after each test
    let origIsImageBlock, origIsTextBlock, origSanitizeContentBlocksImages;

    beforeEach(function() {
        origIsImageBlock = fns.isImageBlock;
        origIsTextBlock = fns.isTextBlock;
        origSanitizeContentBlocksImages = fns.sanitizeContentBlocksImages;
    });

    afterEach(function() {
        // Restore originals to avoid cross-test pollution
        fns.isImageBlock = origIsImageBlock;
        fns.isTextBlock = origIsTextBlock;
        fns.sanitizeContentBlocksImages = origSanitizeContentBlocksImages;
    });

    it('returns the original result when result.content is not an array', async function() {
        const result = { some: 'value' }; // content undefined -> treated as []
        // Make sure helpers would not be accidentally invoked; set them to throw if called
        fns.isImageBlock = () => { throw new Error('isImageBlock should not be called'); };
        fns.isTextBlock = () => { throw new Error('isTextBlock should not be called'); };
        fns.sanitizeContentBlocksImages = async () => { throw new Error('sanitizeContentBlocksImages should not be called'); };

        const out = await sut(result, 'labelX', {opt: 1});
        // When content is not array, function should return the original result object unchanged
        assert.strictEqual(out, result, 'Expected the original result object to be returned');
    });

    })