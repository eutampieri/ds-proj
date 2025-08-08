import { Schema, model } from 'mongoose';
import { User } from '@ldap-proxy-config/models/src/generated/user.js';

import schema from "../../../schemas/user.json"


// Definition of the schema for the client model
const userSchema = new Schema<User>(schema);

// Creation of the client model
export default model("User", userSchema)
