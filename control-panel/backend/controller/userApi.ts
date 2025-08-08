import { Request, Response } from 'express';
import { default as DB } from '../models/userModel';
import { User } from '@ldap-proxy-config/models/src/generated/user.js';
import { Error } from 'mongoose';

export default class API {
    static async createUser(req: Request<{}, {}, User>, res: Response) {
        const user = req.body;
        try {
            const userAlreadyPresent = await DB.findOne({ username: user.user }).exec();
            if (!userAlreadyPresent) {
                await DB.create(user, null);
                res.status(201).json({ message: 'User created successfully' });
            }
            else {
                res.status(500).json({ message: "Username already present" });
            }
        } catch (error) {
            res.status(400).json({ message: (error as Error).message });
        }
    }

    static async fetchAllUsers(_req: Request, res: Response) {
        try {
            const user = await DB.find({}).select("-password").exec();
            res.status(200).json(user);

        } catch (error) {
            res.status(404).json({ message: (error as Error).message })
        }
    }


    static async updateUser(req: Request<{}, {}, User>, res: Response) {
        const id = req.body._id;
        const user: User = {
            user: req.body.user,
            password: req.body.password,
            is_admin: req.body.is_admin,
        };

        try {
            await DB.updateOne({ _id: id }, user, null);
            res.status(200).json({ message: 'User updated successfully' });
        } catch (error) {
            res.status(404).json({ message: (error as Error).message });
        }
    }

    static async deleteUser(req: Request<{ id: string }>, res: Response) {
        const id = req.params.id;
        try {
            // Trova il cliente per ottenere i suoi corsi
            const user = await DB.findById(id);
            if (!user) {
                return res.status(404).json({ message: 'User not found' });
            }

            await DB.findOneAndDelete({ _id: id });

            res.status(200).json({ message: 'User deleted successfully and removed from all courses' });

        } catch (error) {
            res.status(500).json({ message: (error as Error).message });
        }
    }
}
