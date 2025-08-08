import { Request, Response } from 'express';
import { default as DB } from '../models/serverModel';
import { Server } from '@ldap-proxy-config/models/src/generated/server.js';
import { Error } from 'mongoose';

export default class API {
    static async createServer(req: Request<{}, {}, Server>, res: Response) {
        const server = req.body;
        try {
            const serverAlreadyPresent = await DB.findOne({ base_dn: server.base_dn }).exec();
            if (!serverAlreadyPresent) {
                await DB.create(server, null);
                res.status(201).json({ message: 'Server created successfully' });
            }
            else {
                res.status(500).json({ message: "The server's Base DN is already present" });
            }
        } catch (error) {
            res.status(400).json({ message: (error as Error).message });
        }
    }

    static async fetchAllServers(_req: Request, res: Response) {
        try {
            const user = await DB.find({}).select("-bind_password").exec();
            res.status(200).json(user);

        } catch (error) {
            res.status(404).json({ message: (error as Error).message })
        }
    }


    static async updateServer(req: Request<{}, {}, Server>, res: Response) {
        const id = req.body._id;
        const server: Server = {
            base_dn: req.body.base_dn,
            bind_dn: req.body.bind_dn,
            bind_password: req.body.bind_password,
            ip: req.body.ip,
            port: req.body.port,
            tls: req.body.tls,
        };

        try {
            await DB.updateOne({ _id: id }, server, null);
            res.status(200).json({ message: 'Server updated successfully' });
        } catch (error) {
            res.status(404).json({ message: (error as Error).message });
        }
    }

    static async deleteServer(req: Request<{ id: string }>, res: Response) {
        const id = req.params.id;
        try {
            // Trova il cliente per ottenere i suoi corsi
            const client = await DB.findById(id);
            if (!client) {
                return res.status(404).json({ message: 'Server not found' });
            }

            await DB.findOneAndDelete({ _id: id });

            res.status(200).json({ message: 'Server deleted successfully and removed from all courses' });

        } catch (error) {
            res.status(500).json({ message: (error as Error).message });
        }
    }
}
