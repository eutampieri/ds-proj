import { Router } from 'express';
import API from '../controller/clientApi.js';
import { wrapMiddleware, anyAuth } from '../utils.js';

const router = Router();

router.post("/", wrapMiddleware(anyAuth, API.createClient))
router.get("/", wrapMiddleware(anyAuth, API.fetchAllClients))
router.put("/", wrapMiddleware(anyAuth, API.updateClient))
router.delete("/:id", wrapMiddleware(anyAuth, API.deleteClient))

export default router