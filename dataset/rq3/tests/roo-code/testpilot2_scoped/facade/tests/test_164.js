let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.prototype.setMaxListeners', function() {
    // Helper to get the prototype under test
    function getProto() {
      return testpilot_subject
        .file_0012
        .MessageQueueService
        .EventEmitter
        .EventEmitterAsyncResource
        .prototype;
    }

    it('sets _maxListeners to a non-negative integer and returns this for chaining', function() {
      const proto = getProto();
      const obj = Object.create(proto);

      const ret = obj.setMaxListeners(5);
      assert.strictEqual(ret, obj, 'setMaxListeners should return this');
      assert.strictEqual(obj._maxListeners, 5, 'should set _maxListeners to the provided value');

      // chaining should work because the method returns this
      obj.setMaxListeners(2).setMaxListeners(7);
      assert.strictEqual(obj._maxListeners, 7, 'chained calls should update _maxListeners');
    });

        })
})