import { ApiError } from '@/lib/api/errors';
import { config } from '@/lib/config';
import { db } from '@/lib/db';
import { type OAuthProvider, oauthProviderSchema } from '@/lib/db/models/oauth';
import { getUser } from '@/lib/db/models/user';
import { oauthProviders, users } from '@/lib/db/schema';
import { log } from '@/lib/logger';
import enabled from '@/lib/oauth/enabled';
import { userMiddleware } from '@/server/middleware/user';
import typedPlugin from '@/server/typedPlugin';
import { and, eq } from 'drizzle-orm';
import z from 'zod';

export type ApiAuthOauthResponse = OAuthProvider[];

const logger = log('api').c('auth').c('oauth');

export const PATH = '/api/auth/oauth';
export default typedPlugin(
  async (server) => {
    server.get(
      PATH,
      {
        schema: {
          description: 'List OAuth providers currently linked to the authenticated user.',
          response: {
            200: z.array(oauthProviderSchema),
          },
        },
        preHandler: [userMiddleware],
      },
      async (req, res) => {
        return res.send(req.user.oauthProviders);
      },
    );

    server.delete(
      PATH,
      {
        schema: {
          description:
            'Unlink one OAuth provider from the authenticated user, enforcing that at least one login method remains.',
          body: z.object({ provider: oauthProviderSchema.shape.provider }),
          response: {
            200: z.array(oauthProviderSchema),
          },
        },
        preHandler: [userMiddleware],
      },
      async (req, res) => {
        const { provider } = req.body;

        const user = await db.transaction(async (tx) => {
          const [creds] = await tx
            .select({ password: users.password })
            .from(users)
            .where(eq(users.id, req.user.id))
            .for('update');
          if (!creds) throw new ApiError(9002);

          const providers = await tx
            .select({ provider: oauthProviders.provider })
            .from(oauthProviders)
            .where(eq(oauthProviders.userId, req.user.id));
          if (!providers.some((linked) => linked.provider === provider)) throw new ApiError(1030);

          const oauthEnabled = enabled(config);
          const canLogin = providers.some(
            (linked) =>
              linked.provider !== provider &&
              oauthEnabled[linked.provider.toLowerCase() as keyof typeof oauthEnabled],
          );
          if (!creds.password && !canLogin) throw new ApiError(1043);

          await tx
            .delete(oauthProviders)
            .where(and(eq(oauthProviders.userId, req.user.id), eq(oauthProviders.provider, provider)));
          return getUser(req.user.id, tx);
        });
        if (!user) throw new ApiError(9002);

        logger.info(`${req.user.username} unlinked an oauth provider`, {
          provider,
        });

        return res.send(user.oauthProviders);
      },
    );
  },
  { name: PATH },
);
