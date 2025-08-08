import { createSecretKey } from 'crypto';
import { NextFunction, Request, RequestHandler, Response } from 'express';
import { JWTPayload, jwtVerify, JWTVerifyResult } from 'jose';
import { JWT } from "@ldap-proxy-config/models/src/index.js";
import { User } from "@ldap-proxy-config/models/src/generated/user.js";

type FullJWT = JWTPayload & JWT;

const JWT_KEY = createSecretKey(Buffer.from(process.env.JWT_KEY || "secret"));
const ISSUER = process.env.JWT_ISSUER || "iss";
const AUDIENCE = process.env.JWT_AUDIENCE || "aud";

const createAuthMiddleware = (adminRequired: boolean) => async function authMiddleware(req: Request, res: Response, next: NextFunction) {
    if (req.headers["authorization"] !== undefined) {
        let jwt = req.headers["authorization"].split(' ')[1];
        const { payload } = await verifyJWT(jwt);
        const jwt_payload = payload as FullJWT;
        if (payload.error === undefined && (adminRequired ? jwt_payload.is_admin : true)) {
            // JWT is still valid
            (req as any).user = jwt_payload
        } else {
            res.contentType("text/plain").status(401).send(`Invalid token${payload.error === undefined ? "" : ": " + payload.error.code}`);
            return;
        }
    }
    next();
};

const _JWT_KEY = JWT_KEY;
export { _JWT_KEY as JWT_KEY };
const _ISSUER = ISSUER;
export { _ISSUER as ISSUER };
const _AUDIENCE = AUDIENCE;
export { _AUDIENCE as AUDIENCE };
const _createAuthMiddleware = createAuthMiddleware;
export { _createAuthMiddleware as createAuthMiddleware };
export function wrapMiddleware<A, B, C, D, E extends Record<string, any>>(wrapping: RequestHandler<A, B, C, D, E>, wrapped: RequestHandler<A, B, C, D, E>) {
    return (req: Request<A, B, C, D, E>, res: Response<B, E>, next: NextFunction) =>
        wrapping(req, res, () => wrapped(req, res, next));
}
export const adminAuth = createAuthMiddleware(true);
export const anyAuth = createAuthMiddleware(false);

async function verifyJWT(jwt: string): Promise<JWTVerifyResult<FullJWT> | { payload: { error: any; }; protectedHeader: null; }> {
    return await jwtVerify<FullJWT>(jwt, JWT_KEY, {
        issuer: ISSUER,
        audience: [AUDIENCE]
    }).catch((e) => { return { payload: { error: e }, protectedHeader: null }; });
}
