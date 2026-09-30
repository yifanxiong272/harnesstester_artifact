let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0004.cleanSchemaForGemini', function() {

    it('should not mutate the input and should return a new cleaned schema preserving properties', function() {
      const schema = {
        title: 'My Schema',
        type: 'object',
        properties: {
          a: { type: 'string' }
        },
        required: ['a'],
        definitions: {
          X: { type: 'number' }
        }
      };

      // keep a JSON copy to assert non-mutation
      const schemaCopy = JSON.parse(JSON.stringify(schema));

      const result = testpilot_subject.file_0004.cleanSchemaForGemini(schema);

      // result should be an object and not the same reference as input
      assert.ok(result && typeof result === 'object');
      assert.notStrictEqual(result, schema);

      // input should remain unchanged
      assert.deepStrictEqual(schema, schemaCopy);

      // expected fields should be preserved in the cleaned result
      assert.strictEqual(result.title, schema.title);
      assert.ok(result.properties && result.properties.a && result.properties.a.type === 'string');
    });

        })
})