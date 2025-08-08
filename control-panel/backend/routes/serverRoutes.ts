import { Router } from 'express';
import API from '../controller/serverApi.js';
import { wrapMiddleware, anyAuth } from '../utils.js';

const router = Router();

router.post("/", wrapMiddleware(anyAuth, API.createServer))
router.get("/", wrapMiddleware(anyAuth, API.fetchAllServers))
router.put("/", wrapMiddleware(anyAuth, API.updateServer))
router.delete("/:id", wrapMiddleware(anyAuth, API.deleteServer))

export default router