import { it, expect } from 'vitest'
import { parseTelegramReplyToMessageId } from '../../../extensions/telegram/src/outbound-params'

it('parseTelegramReplyToMessageId should reject strings with trailing nondigits like "123abc"', () => {
  const result = parseTelegramReplyToMessageId('123abc')
  expect(result).toBeUndefined()
})
