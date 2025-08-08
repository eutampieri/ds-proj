import { Schema, model } from 'mongoose';
import { Server } from '@ldap-proxy-config/models/src/generated/server.js';

import schema from "../../../schemas/server.json"


// Definition of the schema for the server model
const serverSchema = new Schema<Server>(schema);

// Creation of the server model
export default model("Server", serverSchema)
