import { it, expect } from 'vitest';
import { buildTelegramSendParams } from '../../../extensions/telegram/src/bot/delivery.send';

it('propagates explicitly supplied numeric replyToMessageId (including 0) and sets allow_sending_without_reply; respects silent', () => {
  const outZero = buildTelegramSendParams({ replyToMessageId: 0 });
  const outPos = buildTelegramSendParams({ replyToMessageId: 42, silent: true });

  expect([outZero, outPos]).toEqual([
    { reply_to_message_id: 0, allow_sending_without_reply: true },
    { reply_to_message_id: 42, allow_sending_without_reply: true, disable_notification: true },
  ]);
});
