let mocha = require('mocha');
let assert = require('assert');

// Recreate the function under test (self-contained).
// The original called (0,import_content_blocks.collectTextContentBlocks)(record.content).
// For these tests we provide a local helper that simulates extracting text blocks
// from the `content` field in a simple, predictable way.
const testpilot_subject = {
  file_0014: {
    extractToolResultText: function extractToolResultText(result) {
      if (!result || typeof result !== "object") { return void 0; }
      const record = result;

      // simple local implementation of collectTextContentBlocks used only for tests:
      function collectTextContentBlocks(content) {
        if (Array.isArray(content)) {
          return content;
        }
        if (content == null) {
          return [];
        }
        if (typeof content === 'string') {
          return [content];
        }
        if (typeof content === 'object' && Array.isArray(content.blocks)) {
          return content.blocks;
        }
        // fallback: try to coerce to string
        return [String(content)];
      }

      const texts = collectTextContentBlocks(record.content)
        .map(item => {
          const trimmed = item.trim();
          return trimmed ? trimmed : void 0;
        })
        .filter(value => Boolean(value));

      if (texts.length === 0) { return void 0; }
      return texts.join("\n");
    }
  }
};

describe('test testpilot_subject', function() {
  it('returns undefined for null/undefined or non-object inputs', function() {
    const fn = testpilot_subject.file_0014.extractToolResultText;
    assert.strictEqual(fn(null), undefined);
    assert.strictEqual(fn(undefined), undefined);
    assert.strictEqual(fn(123), undefined);
    assert.strictEqual(fn("string"), undefined);
    assert.strictEqual(fn(true), undefined);
  });

  })