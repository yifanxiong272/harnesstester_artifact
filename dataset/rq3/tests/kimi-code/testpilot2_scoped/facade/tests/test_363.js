let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0002.KimiCore.prototype.installPlugin', function() {
  // grab the method under test from the prototype so we can attach it to plain objects
  const installPlugin = testpilot_subject.file_0002.KimiCore.prototype.installPlugin;

  it('returns the matching summary when install returns a record with an id present in summaries()', async function() {
    let assertCalled = 0;

    const obj = {
      // pluginsReady resolved immediately
      pluginsReady: Promise.resolve(),
      assertPluginsLoaded() { assertCalled++; },
      plugins: {
        // simulate install returning a record with id
        install: async (source) => ({ id: 'plugin-1', source }),
        // summaries returns an array containing the matching summary
        summaries: () => [{ id: 'plugin-1', name: 'Test Plugin' }]
      },
      // attach the prototype method so `this` works
      installPlugin
    };

    const payload = { source: 'dummy-source' };
    const result = await obj.installPlugin(payload);

    // assertPluginsLoaded was called
    assert.strictEqual(assertCalled, 1);
    // result should be the summary object with matching id
    assert.deepStrictEqual(result, { id: 'plugin-1', name: 'Test Plugin' });
  });

  })