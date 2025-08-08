import { Request, Response } from 'express';
import { default as DB } from '../models/clientModel';
import { Client } from '@ldap-proxy-config/models/src/generated/client.js';
import { Error } from 'mongoose';

export default class API {
    static async createClient(req: Request<{}, {}, Client>, res: Response) {
        const client = req.body;
        try {
            const clientAlreadyPresent = await DB.findOne({ dn: client.dn }).exec();
            if (!clientAlreadyPresent) {
                await DB.create(client, null);
                res.status(201).json({ message: 'Client created successfully' });
            }
            else {
                res.status(500).json({ message: "DN already present" });
            }
        } catch (error) {
            res.status(400).json({ message: (error as Error).message });
        }
    }

    static async fetchAllClients(_req: Request, res: Response) {
        try {
            const user = await DB.find({}).select("dn").exec();
            res.status(200).json(user);

        } catch (error) {
            res.status(404).json({ message: (error as Error).message })
        }
    }


    static async updateClient(req: Request<{}, {}, Client>, res: Response) {
        const id = req.body._id;
        const client: Client = {
            dn: req.body.dn,
            password: req.body.password,
        };

        try {
            await DB.updateOne({ _id: id }, client, null);
            res.status(200).json({ message: 'Client updated successfully' });
        } catch (error) {
            res.status(404).json({ message: (error as Error).message });
        }
    }

    static async deleteClient(req: Request<{ id: string }>, res: Response) {
        const id = req.params.id;
        try {
            // Trova il cliente per ottenere i suoi corsi
            const client = await DB.findById(id);
            if (!client) {
                return res.status(404).json({ message: 'Client not found' });
            }

            await DB.findOneAndDelete({ _id: id });

            res.status(200).json({ message: 'Client deleted successfully and removed from all courses' });

        } catch (error) {
            res.status(500).json({ message: (error as Error).message });
        }
    }
}
