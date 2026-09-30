let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0014.TagMatcher.prototype.collect', function() {
    // Helper: get TagMatcher constructor
    function getTagMatcherCtor() {
      if (!testpilot_subject || !testpilot_subject.file_0014) {
        throw new Error('testpilot_subject.file_0014 not found');
      }
      const TagMatcher = testpilot_subject.file_0014.TagMatcher;
      if (!TagMatcher) throw new Error('TagMatcher not found at testpilot_subject.file_0014.TagMatcher');
      return TagMatcher;
    }

    // Helper: create an instance of TagMatcher in a resilient way
    function createInstance(TagMatcher) {
      // Try to construct normally
      try {
        return new TagMatcher();
      } catch (e) {
        // Try as plain function
        try {
          return TagMatcher();
        } catch (e2) {
          // Fallback: create an object with TagMatcher.prototype as prototype
          const proto = TagMatcher.prototype || {};
          const inst = Object.create(proto);
          // If collect is a static function on the constructor, attach it so tests can call it
          if (typeof TagMatcher.collect === 'function' && typeof inst.collect !== 'function') {
            inst.collect = TagMatcher.collect;
          }
          return inst;
        }
      }
    }

    // Helper: call collect and return a Promise for the result (handles sync or Promise-returning collect)
    function runCollect(inst, input) {
      try {
        const res = inst.collect(input);
        if (res && typeof res.then === 'function') {
          return res;
        }
        return Promise.resolve(res);
      } catch (err) {
        return Promise.reject(err);
      }
    }

    it('exists and is callable', function() {
      const TagMatcher = getTagMatcherCtor();
      assert.ok(typeof TagMatcher === 'function' || typeof TagMatcher === 'object', 'TagMatcher should be a constructor/function/object');
      const inst = createInstance(TagMatcher);
      assert.ok(inst, 'instance should be created');
      assert.ok(typeof inst.collect === 'function', 'instance.collect should be a function');
    });

        })
})