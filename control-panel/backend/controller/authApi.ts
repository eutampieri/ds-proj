import { default as UserDB } from '../models/userModel';
import { User } from '@ldap-proxy-config/models/src/generated/user.js';
import { SignJWT } from 'jose';
import { JWT_KEY, ISSUER, AUDIENCE } from '../utils.js';
import { verify } from '@node-rs/argon2';
import { Request, Response } from 'express';
import { AuthRequest } from '@ldap-proxy-config/models/src/requests.js';
import { JWT } from "@ldap-proxy-config/models/src/index.js";

async function lookupUsername(username: string): Promise<User | null> {
    const result = (await UserDB.findOne({ username }).exec() as User | undefined | null);
    if (result) {
        return result;
    } else {
        return null;
    }
}

export async function authenticate(req: Request<{}, {}, AuthRequest>, res: Response) {
    const { username, password } = req.body;
    const token = {};

    try {
        const user = await lookupUsername(username);
        if (user === null || !await verify(user.password, password)) {
            res.status(401).send("Unauthorized");
        } else {
            const token: JWT = {
                username: user.user,
                isAdmin: user.is_admin,
            };
            const jwt = await new SignJWT(token as any) // details to  encode in the token
                .setProtectedHeader({
                    alg: 'HS256'
                }) // algorithm
                .setIssuedAt()
                .setIssuer(ISSUER) // issuer
                .setAudience(AUDIENCE) // audience
                .setExpirationTime("1 day") // FIXME sketchy
                .sign(JWT_KEY);
            res.contentType("text/plain").send(jwt);
        }
    } catch (error) {
        console.error('Error during authentication:', error);
        res.status(500).send('Error during authentication');
    }
}
