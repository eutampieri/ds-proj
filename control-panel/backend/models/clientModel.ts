import { Schema, model } from 'mongoose';
import { Client } from '@ldap-proxy-config/models/src/generated/client.js';

import schema from "../../../schemas/client.json"


// Definition of the schema for the client model
const clientSchema = new Schema<Client>(schema);

// Creation of the client model
export default model("Client", clientSchema)
