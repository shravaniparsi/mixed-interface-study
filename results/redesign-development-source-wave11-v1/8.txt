import { config } from '@/lib/config';
import { db } from '@/lib/db';
import { userSessions } from '@/lib/db/schema';
import { log } from '@/lib/logger';
import { oidcLogoutURL } from '@/lib/oauth/providers';
import { userMiddleware } from '@/server/middleware/user';
import { getSession } from '@/server/session';
import typedPlugin from '@/server/typedPlugin';
import { and, eq } from 'drizzle-orm';
import z from 'zod';

export type ApiLogoutResponse = {
  loggedOut?: boolean;
  redirectUrl?: string;
};

const logger = log('api').c('auth').c('logout');

export const PATH = '/api/auth/logout';
export default typedPlugin(
  async (server) => {
    server.get(
      PATH,
      {
        schema: {
          description:
            'Invalidate the active session and optionally return an OIDC logout URL for the browser to visit.',
          response: {
            200: z.object({
              loggedOut: z.boolean().optional(),
              redirectUrl: z.string().optional(),
            }),
          },
          tags: ['auth'],
        },
        preHandler: [userMiddleware],
      },
      async (req, res) => {
        const current = await getSession(req, res);

        const [deletedSession] = await db
          .delete(userSessions)
          .where(and(eq(userSessions.userId, req.user.id), eq(userSessions.id, current.sessionId!)))
          .returning({
            oauthProvider: userSessions.oauthProvider,
            oidcIdToken: userSessions.oidcIdToken,
          });

        current.destroy();

        logger.info('user logged out', {
          user: req.user.username,
          ip: req.ip ?? 'unknown',
          ua: req.headers['user-agent'],
        });

        let redirectUrl: string | undefined;
        const oidc = config.oauth.oidc;
        if (deletedSession?.oauthProvider === 'OIDC' && oidc?.endSessionUrl && oidc.clientId) {
          try {
            const origin = `${config.core.returnHttpsUrls ? 'https' : 'http'}://${req.host}`;
            const postLogoutRedirectUri = new URL(
              '/auth/login?logged_out=true',
              oidc.redirectUri ?? origin,
            ).toString();

            redirectUrl = oidcLogoutURL({
              endSessionUrl: oidc.endSessionUrl,
              clientId: oidc.clientId,
              postLogoutRedirectUri,
              idToken: deletedSession.oidcIdToken,
            });
          } catch {
            logger.warn('could not build the OIDC logout URL');
          }
        }

        return res.header('Cache-Control', 'no-store').send({ loggedOut: true, redirectUrl });
      },
    );
  },
  { name: PATH },
);
