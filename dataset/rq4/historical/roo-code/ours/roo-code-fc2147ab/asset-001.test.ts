import { BaseOpenAiCompatibleProvider } from '../../api/providers/base-openai-compatible-provider'

test('completePrompt returns empty string when API response omits choices', async () => {
  // Deterministic mock client that returns {} (no `choices`)
  const mockClient = {
    chat: {
      completions: {
        create: async () => {
          return {}
        },
      },
    },
  }

  // Fabricate an object whose prototype is the provider prototype so we can
  // call the instance method without invoking unknown constructors.
  const fakeInstance: any = Object.create(BaseOpenAiCompatibleProvider.prototype)
  // Provide the minimal properties the implementation accesses.
  fakeInstance.client = mockClient
  fakeInstance.providerName = 'test-provider'
  fakeInstance.getModel = () => ({ id: 'test-model' })

  // Call the public entrypoint using the fabricated `this`.
  const promise = BaseOpenAiCompatibleProvider.prototype.completePrompt.call(fakeInstance, 'sample prompt')

  // Single expect: the independent oracle requires the method to resolve to ''.
  await expect(promise).resolves.toBe('')
})
