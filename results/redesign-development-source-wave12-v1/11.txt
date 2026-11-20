import { userSessions } from '@/lib/db/schema';
import { createSelectSchema } from 'drizzle-orm/zod';
import { z } from 'zod';

export const userSessionSchema = createSelectSchema(userSessions).omit({
  oauthProvider: true,
  oidcIdToken: true,
});
export type UserSession = z.infer<typeof userSessionSchema>;
