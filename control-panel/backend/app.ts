import express, { json } from 'express';
import { connect } from 'mongoose';
import logger from 'morgan';
import { hash } from '@node-rs/argon2';
import { default as UserDB } from "./models/userModel";
import { User } from "@ldap-proxy-config/models/src/generated/user.js";

import clients from './routes/clientRoutes';
import servers from './routes/serverRoutes';
import users from './routes/userRoutes';
import auth from './routes/authRoutes';


// Inizializziamo l'applicazione Express
const app = express();

// Configuriamo i middleware
app.use(logger('dev'));
app.use(json());

const uri = process.env.MONGODB_URI || 'mongodb://localhost:27017/ldap-proxy-database';

connect(uri, {})
  .then(() => {
    console.log('Connection to database successful');

    createDefaultAdmin();
  })
  .catch((error) => {
    console.error('Errore connecting to the database:', error.message);
  });


async function createDefaultAdmin() {
  try {
    const admins = await UserDB.find({ is_admin: true }).exec();
    if (admins.length === 0) {
      const admin: User = {
        user: 'admin',
        password: await hash('admin'),
        is_admin: true,
      };
      await UserDB.create(admin, null);
      console.log('Admin di default creato con successo.');
    } else {
      console.log('Admin di default già esistente.');
    }
  } catch (error) {
    console.error('Errore nella creazione dell\'admin di default:', error);
  }
}

app.use('/api/auth', auth);
app.use('/api/clients', clients);
app.use('/api/servers', servers);
app.use('/api/users', users);

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});

